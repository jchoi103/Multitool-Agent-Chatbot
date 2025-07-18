# Installation

Follow these steps to set up the project:

1. Get an openai api key and a llamaindex api key and put them in an .env file with the names LLAMA_CLOUD_API_KEY=your-api-key and OPENAI_API_KEY=your-api-key

2. Create a virtual environment (optional):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Unix/macOS
   # or
   .\venv\Scripts\activate  # On Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the CLI:
   ```bash
   python llamacli.py
   ```

If you want to run the parser (This will take a while since it's a big file to parse):

```bash
python llamaparse.py
```

This will generate the stored_index folder but you need the catalog.pdf (or whatever file you chose to use) in the same directory
