from llama_index.readers.json import JSONReader
from llama_index.core import VectorStoreIndex
import openai
import os
from dotenv import load_dotenv
load_dotenv()


openai.api_key = os.getenv("OPENAI_API_KEY")

documents = JSONReader().load_data(input_file="./miniCatalog.json", extra_info={})

index = VectorStoreIndex.from_documents(documents)

index.storage_context.persist(persist_dir="./stored_index_miniCatalog")
