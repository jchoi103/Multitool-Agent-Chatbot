import openai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

client = openai.OpenAI(
    base_url="http://0.0.0.0:4000",
    api_key=api_key,
)

print("Welcome to LitLLM's Proxy chatbot, to exit type: q or quit")
while True:
    user_input = input("User: ")
    if user_input.lower() in ["q", "quit"]:
        break  
    try:
        response = client.chat.completions.create(
            model="uxly-model",
            messages=[{"role": "user", "content": f"<question>{user_input}</question>"}],
            extra_body={"guardrails": ["aporia-pre-guard", "aporia-post-guard"]}
        )
        bot_response = response.choices[0].message.content
        print(f"UXly-model: {bot_response}")
    except Exception as e:
        try:
            error_data = e.response.json()
            error = error_data.get("error", {})
            message = error.get("message", {}).get("error", "Unknown error")
            aporia_ai_response = error.get("message", {}).get("aporia_ai_response", {})
            revised_response = aporia_ai_response.get("revised_response", "No revision")
            print(f"Error Detected: {message}")
            print(f"Aporia's Response: {revised_response}")
        except:
            print(f"Unexpected Error: {str(e)}")