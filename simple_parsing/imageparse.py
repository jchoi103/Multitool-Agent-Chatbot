import logging
import shutil
from llama_cloud_services import LlamaParse
from openai import OpenAI
import json
import os
import base64
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# clear or create image folder
if not os.path.exists('images'):
    os.makedirs('images')
else:
    shutil.rmtree('images')
    os.makedirs('images')

openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

parser = LlamaParse(verbose=True, structured_output=True)
json_objs = parser.get_json_result("./catalog.pdf")
pages = json_objs[0]["pages"]

images = parser.get_images(json_objs, download_path="./images")


def describe_image(file_path):
    prompt = """Please analyze the image.
If the image primarily features text, respond with "no".
Otherwise, describe the image in 5-7 words. If you cannot determine what the image depicts, give it an educated guess otherwise respond with "no."
"""
    with open(file_path, "rb") as image_file:
        b64_image = base64.b64encode(image_file.read()).decode('utf-8')
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_image}"}}
            ]}
        ],
        max_tokens=100,
    )
    return response.choices[0].message.content.strip()


for page in pages:
    new_images = []
    for image in page.get("images", []):
        # Get rid of unnecessary keys
        for key in ["height", "charts", "width", "x", "y", "original_width", "original_height", "ocr", "job_id", "original_file_path", "status", "links", "triggeredAutoMode", "parsingMode", "structuredData", "noStructuredContent", "noTextContent"]:
            image.pop(key, None)
        for item in page.get("items", []):
            item.pop("bBox", None)
        img_path = image.get("path")
        if img_path:
            description = describe_image(img_path)
            print(f"Description for {img_path}: {description}")
            if len(description) <= 5:
                continue
            else:
                image["description"] = description
        new_images.append(image)
    page["images"] = new_images


with open("catalog_images.json", "w") as f:
    json.dump(pages, f, indent=4)
