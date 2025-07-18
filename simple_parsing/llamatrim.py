import json
import time
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv
import jsonschema
import concurrent.futures
import threading
import re

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("Please set OPENAI_API_KEY environment variable")

api_call_counter = 0
api_call_lock = threading.Lock()


def make_api_call(llm, messages):
    global api_call_counter
    with api_call_lock:
        api_call_counter += 1
        print(f"API call count: {api_call_counter}")
    return llm.invoke(messages)


def read_input_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()


def chunk_text(text):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=6000,  # used to be 2000 but i want this to run faster and not hit the rate limit so here we are
        chunk_overlap=500,
        length_function=len
    )
    return text_splitter.split_text(text)


def enforce_item_formatting(item, llm):
    correction_prompt = f"""Correct the formatting of the following product item JSON object so that it strictly adheres 
to a schema with the following properties: 
- partNo: string
- size: string
- misc: list of strings

Any extra keys (other than partNo, size) should be moved into misc and all values converted to strings. If there are none leave as an empty list.
Output valid JSON without markdown formatting.
Item: {json.dumps(item)}"""
    try:
        from langchain_core.messages import HumanMessage
        messages = [HumanMessage(content=correction_prompt)]
        response = make_api_call(llm, messages)
        response_text = response.content if hasattr(
            response, 'content') else str(response)
        if "```json" in response_text:
            response_text = response_text.split(
                "```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].strip()
        new_item = json.loads(response_text)
        return new_item
    except Exception as e:
        with open("error_logs.txt", "a") as log:
            log.write(
                f"Error enforcing item formatting: {e}. Original item: {json.dumps(item)}\n")
        allowed = {"manufacturer", "partNo", "size", "price", "misc"}
        fallback_item = {}
        fallback_item["misc"] = []
        for key, value in item.items():
            if key in allowed:
                fallback_item[key] = str(value) if not isinstance(
                    value, str) else value
            else:
                fallback_item["misc"].append(f"{key}: {value}")
        for k in ["manufacturer", "partNo", "size", "price", "misc"]:
            if k not in fallback_item:
                fallback_item[k] = "" if k != "misc" else []
        return fallback_item


def process_chunk(chunk, llm):
    system_message = """You are a JSON formatting assistant. Convert the input text into JSON with product information.
When processing table data, consolidate all columns from each row into a single JSON object.
Ensure that if a row contains extra information such as Neutral, Code Name, Lbs. / 1000', or Put-Ups,
these values are included in the appropriate fields – if they do not belong to a defined field, add them to "misc"."""
    example = {
        "products": [
            {
                "name": "",
                "Description": "",
                "Features": [],
                "items": [
                    {
                        "partNo": "",
                        "size": "",
                        "misc": []
                    }
                ],
                "misc": []
            }
        ]
    }
    prompt = f"""Convert this text to JSON using this structure:
{json.dumps(example, indent=2)}
Note: If the text contains table rows, consolidate all columns into a single JSON object for each row.
For table rows, parse size columns into "size" (e.g. AWG Size, size etc) and any other columns (e.g. Neutral, Code Name, Lbs. / 1000', Put-Ups) into the "misc" list.
Use the provided text below to extract product information.
Text to process:
{chunk}"""
    try:
        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=prompt)
        ]
        response = make_api_call(llm, messages)
        response_text = response.content if hasattr(
            response, 'content') else str(response)
        json_content = response_text.strip()
        if "```json" in json_content:
            json_content = json_content.split(
                "```json")[1].split("```")[0].strip()
        elif "```" in json_content:
            json_content = json_content.split("```")[1].strip()
        result = json.loads(json_content)

        schema = {
            "type": "object",
            "properties": {
                "products": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "Description": {"type": "string"},
                            "Features": {"type": "array", "items": {"type": "string"}},
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "partNo": {"type": "string"},
                                        "size": {"type": "string"},
                                        "misc": {"type": "array", "items": {"type": "string"}}
                                    },
                                    "required": ["partNo", "size", "misc"]
                                }
                            },
                            "misc": {"type": "array"}
                        },
                        "required": ["name", "Description", "Features", "items", "misc"]
                    }
                }
            },
            "required": ["products"]
        }
        jsonschema.validate(instance=result, schema=schema)

        blacklist = {"misc: []", "misc: {}",
                     "key: value", "extraKey1: extraValue1", "extraKey2: extraValue2", "extraKey3: extraValue3"}
        for product in result.get("products", []):
            for item in product.get("items", []):
                if "misc" in item and isinstance(item["misc"], list):
                    item["misc"] = [entry for entry in item["misc"]
                                    if entry not in blacklist]
        return result
    except Exception as e:
        error_message = f"Error processing chunk: {e}. Raw chunk: {chunk[:100]}..."
        with open("error_logs.txt", "a") as log:
            log.write(error_message + "\n")
        try:
            partial_result = {"raw": json_content, "error": str(e)}
        except Exception:
            partial_result = {"error": str(e), "raw": chunk}
        return partial_result


def is_all_caps(text):
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and text.upper() == text


def merge_chunk_results(results):
    all_products = []
    for res in results:
        all_products.extend(res.get("products", []))

    merged = []
    current_product = None

    for prod in all_products:
        name = prod.get("name", "").strip()
        if is_all_caps(name):
            if current_product:
                merged.append(current_product)
            current_product = prod.copy()
            current_product["items"] = prod.get("items", []).copy()
            current_product["Features"] = prod.get("Features", []).copy()
            current_product["misc"] = prod.get("misc", []).copy()
        else:
            if current_product:
                current_product["items"].extend(prod.get("items", []))
                for field in ["Features", "misc"]:
                    for entry in prod.get(field, []):
                        if entry not in current_product[field]:
                            current_product[field].append(entry)
            else:
                current_product = prod.copy()
                current_product["items"] = prod.get("items", []).copy()
                current_product["Features"] = prod.get("Features", []).copy()
                current_product["misc"] = prod.get("misc", []).copy()

    if current_product:
        merged.append(current_product)
    return {"products": merged}


def is_part_number(name):
    return bool(re.fullmatch(r'\d{4,}', name.strip()))


def validate_and_shift_products(merged_result):
    products = merged_result.get("products", [])
    validated = []
    for prod in products:
        name = prod.get("name", "").strip()
        if is_part_number(name) and validated:
            prev = validated[-1]
            prev["items"].extend(prod.get("items", []))
            for field in ["Features", "misc"]:
                for entry in prod.get(field, []):
                    if entry not in prev[field]:
                        prev[field].append(entry)
        else:
            validated.append(prod)
    return {"products": validated}


def consolidate_items(merged_result):
    for prod in merged_result.get("products", []):
        grouped = {}
        for item in prod.get("items", []):
            part = item.get("partNo", "").strip()
            if part in grouped:
                existing = grouped[part]
                if not existing.get("size") and item.get("size"):
                    existing["size"] = item["size"]
                for val in item.get("misc", []):
                    if val not in existing["misc"]:
                        existing["misc"].append(val)
            else:
                grouped[part] = {
                    "partNo": part,
                    "size": item.get("size", ""),
                    "misc": item.get("misc", []).copy()
                }
        prod["items"] = list(grouped.values())
    return merged_result


def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    llm = ChatOpenAI(
        temperature=0.1,
        model_name="gpt-4o-mini",
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    start_time = time.time()
    input_text = read_input_file('trimmed_data.txt')
    chunks = chunk_text(input_text)
    total_chunks = len(chunks)
    print(f"Created {total_chunks} chunks")

    results_dict = {}
    processed_chunks = set()
    lock = threading.Lock()
    completed = 0

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(
                process_chunk, chunk, llm): i for i, chunk in enumerate(chunks, 1)}
            for future in concurrent.futures.as_completed(futures):
                i = futures[future]
                result = future.result()
                with lock:
                    if "error" not in result and i not in processed_chunks:
                        results_dict[i] = result
                        processed_chunks.add(i)
                completed += 1
                elapsed = time.time() - start_time
                avg_time = elapsed / completed
                eta = avg_time * (total_chunks - completed)
                logging.info(
                    f"Chunk {i}/{total_chunks} processed. Estimated ETA: {eta:.2f} seconds")
                print(
                    f"Processed chunk {i}/{total_chunks}. Estimated ETA: {eta:.2f} seconds")
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt detected! Saving processed data so far...")
    finally:
        results = [results_dict[k] for k in sorted(results_dict.keys())]
        merged_result = merge_chunk_results(results)
        validated_result = validate_and_shift_products(merged_result)
        consolidated_result = consolidate_items(validated_result)

        try:
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(consolidated_result, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logging.error(f"Error writing to file: {e}")

        print("Processing complete!")
        print(f"Processed {len(results)} chunks successfully")


if __name__ == "__main__":
    main()
