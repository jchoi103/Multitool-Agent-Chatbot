import json
import os
import time
import logging
import concurrent.futures
import threading
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv
import jsonschema

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("Please set OPENAI_API_KEY environment variable")
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_raw_text(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def refine_item(item, llm):
    prompt = f"""You are a JSON refining assistant. The following product item JSON object may have missing or incomplete fields.
The item must follow this schema:
{{
    "partNo": "string",
    "size": "string",
    "misc": ["string"]  // array of strings for extra information
}}

Ensure that 'partNo' and 'size' are correct strings and that any missing extra data is filled into the 'misc' list.
Do not remove any existing good data.
Item: {json.dumps(item)}
Output valid JSON without markdown formatting."""
    messages = [
        SystemMessage(content="You are a JSON refining assistant."),
        HumanMessage(content=prompt)
    ]
    try:
        response = llm.invoke(messages)
        response_text = response.content if hasattr(
            response, 'content') else str(response)
        if "```json" in response_text:
            response_text = response_text.split(
                "```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].strip()
        return json.loads(response_text)
    except Exception as e:
        logging.error(f"Error refining item {item.get('partNo')}: {e}")
        return item


def refine_product(product, llm):
    refined_items = []
    for item in product.get("items", []):
        if not item.get("partNo") or not item.get("size"):
            refined = refine_item(item, llm)
        else:
            refined = item
        refined_items.append(refined)
    product["items"] = refined_items

    for item in product.get("items", []):
        for extra in item.get("misc", []):
            if extra not in product.get("misc", []):
                product.setdefault("misc", []).append(extra)
    return product


def verify_product_against_raw(product, raw_text, llm):
    prompt = f"""You are an assistant that verifies JSON data against raw text.
The product must follow this schema:
{{
    "name": "string",
    "Description": "string",
    "Features": ["string"],
    "items": [
        {{
            "partNo": "string",
            "size": "string",
            "misc": ["string"]
        }}
    ],
    "misc": ["string"]
}}

The following product JSON may be missing data present in the raw text.
Raw text:
\"\"\"{raw_text}\"\"\"
Product JSON:
{json.dumps(product, indent=2)}
Please return a corrected product JSON that includes any extra details found in the raw text.
Output valid JSON without markdown formatting."""
    messages = [
        SystemMessage(
            content="You are an assistant that verifies and corrects product JSON data based on raw text."),
        HumanMessage(content=prompt)
    ]
    try:
        response = llm.invoke(messages)
        response_text = response.content if hasattr(
            response, 'content') else str(response)
        if "```json" in response_text:
            response_text = response_text.split(
                "```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].strip()
        return json.loads(response_text)
    except Exception as e:
        logging.error(
            f"Verification error for product '{product.get('name')}': {e}")
        return product


def process_product(product, raw_text, llm):
    refined = refine_product(product, llm)
    verified = verify_product_against_raw(refined, raw_text, llm)
    return verified


def validate_schema(data):
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
    jsonschema.validate(instance=data, schema=schema)
    return data


def process_all_products(data, raw_text, llm):
    products = data.get("products", [])
    total = len(products)
    results_dict = {}
    processed_products = set()
    lock = threading.Lock()
    completed = 0
    start_time = time.time()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(process_product, product, raw_text, llm): i
                       for i, product in enumerate(products)}

            for future in concurrent.futures.as_completed(futures):
                i = futures[future]
                result = future.result()
                with lock:
                    if i not in processed_products:
                        results_dict[i] = result
                        processed_products.add(i)
                completed += 1
                elapsed = time.time() - start_time
                avg_time = elapsed / completed
                eta = avg_time * (total - completed)
                logging.info(
                    f"Processed product {completed}/{total}. ETA: {eta:.2f} seconds")

    except Exception as e:
        logging.error(f"Error in concurrent processing: {e}")
        raise
    results = [results_dict[k] for k in sorted(results_dict.keys())]
    data["products"] = results
    return validate_schema(data)


def clean_json(data):
    products = data.get("products", [])
    cleaned_products = []

    for i, product in enumerate(products):
        if not product.get("name", "").strip():
            continue
        if (not product.get("items") and
            not product.get("Features") and
                not product.get("Description", "").strip()):
            continue
        # If this product's name matches the first item's part number
        # and there's a previous product, merge items into previous product
        if (cleaned_products and product.get("items") and
                product["name"].strip() == product["items"][0].get("partNo", "").strip()):
            cleaned_products[-1]["items"].extend(product.get("items", []))
            if product.get("misc"):
                cleaned_products[-1].setdefault("misc",
                                                []).extend(product["misc"])
            continue

        cleaned_products.append(product)

    return {"products": cleaned_products}


def second_pass(data, raw_text, llm):
    return process_all_products(data, raw_text, llm)


def main():
    start_time = time.time()
    input_file = 'data.json'
    raw_text_file = 'trimmed_data.txt'
    output_file = 'refined_data.json'

    data = load_json(input_file)
    raw_text = load_raw_text(raw_text_file)

    llm = ChatOpenAI(
        temperature=0.1,
        model_name="gpt-4o-mini",
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    logging.info("Starting JSON cleaning phase...")
    cleaned_data = clean_json(data)

    # Process the cleaned data through second pass
    # logging.info("Starting second pass processing...")
    # processed_data = second_pass(cleaned_data, raw_text, llm)

    validate_schema(cleaned_data)
    write_json(cleaned_data, output_file)

    elapsed = time.time() - start_time
    logging.info(f"Processing complete! Output written to {output_file}.")
    logging.info(f"Second pass completed in {elapsed:.2f} seconds.")


if __name__ == "__main__":
    main()
