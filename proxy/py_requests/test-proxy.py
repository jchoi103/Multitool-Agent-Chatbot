# pip install openai

import openai

client = openai.OpenAI(
    api_key="None", 
    base_url="http://0.0.0.0:4000")

response = client.chat.completions.create(
    model="uxly-model", messages=[{"role": "user", "content": "write me a short poem"}]
)

print(response)
