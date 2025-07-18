from llama_index.core import StorageContext, load_index_from_storage
from llama_index.llms.openai import OpenAI
from llama_index.core import PromptTemplate
import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

llm = OpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
    api_key=os.getenv("OPENAI_API_KEY")
)

system_prompt = """You are a helpful assistant specialized in providing information about industrial parts and fittings.
Please follow these guidelines:
1. Provide clear, concise answers
2. Include part numbers when available
3. Format measurements and specifications consistently
4. If information is not available, say so directly
5. Stick to factual information from the provided documents
6. Answer in plaintext not markdown
"""

query_prompt_tmpl = """Context information is below.
---------------------
{context_str}
---------------------
Given this information, please answer the question: {query_str}
Remember to be precise and include specific part numbers and measurements when available.
If you cannot find the exact information, please say so clearly.
"""

storage_context = StorageContext.from_defaults(
    persist_dir="./stored_index_miniCatalog")
index = load_index_from_storage(storage_context)

query_engine = index.as_query_engine(
    llm=llm,
    system_prompt=system_prompt,
    text_qa_template=PromptTemplate(query_prompt_tmpl)
)

# queries = [
#     "What sizes are available for the 45 degree elbow from Pierce?",
#     "List all Travis part numbers for the WeldOnStarterCoupler",
#     "What types of fittings are available?"
# ]

# print("\nRunning predefined queries:")
# for query in queries:
#     print(f"\nQuery: {query}")
#     response = query_engine.query(query)
#     print(f"Response: {response}")

print("\nStarting interactive mode:")


def ask_question():
    while True:
        query = input("\nEnter your question (or 'quit' to exit): ")
        if query.lower() == 'quit':
            break

        response = query_engine.query(query)
        print(f"Response: {response}")


if __name__ == "__main__":
    ask_question()
