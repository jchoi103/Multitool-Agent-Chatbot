Go to console.groq.com

Create account

Go to API Keys > Create API Key, pick whatever name

make a .env file with (aporia info will be provided in google drive: 
https://docs.google.com/document/d/1l8yg5-6OhS0G1Kj86ZCJUfkAwlvyGsBzRuT6XxKrvTM/edit?tab=t.0#heading=h.izudvfv7csgr)

```bash
OPENAI_API_KEY=your-api-key

APORIA_API_KEY_1=your_api_key
APORIA_API_BASE_1=your_projects_base 

APORIA_API_KEY_2=your_api_key
APORIA_API_BASE_2=your_projects_base
```

RECOMMENDED - Create a py environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Download LitLLM: 
```bash
pip install 'litellm[proxy]'
```

pip install 
Install the dependencies - mainly just need Open AI and requests: 
```bash
pip install -r requirements.txt
```

Run:
```bash
docker compose up --build
```

in another terminal:
```bash
./XXXX.sh

python XXXX.py
```

To stop:
```bash
docker compose down
```
