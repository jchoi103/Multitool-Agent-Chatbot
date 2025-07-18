# Chatbot 
## Setup

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the backend directory:
```
OPENAI_API_KEY=your_api_key_here
LLAMA_CLOUD_API_KEY=your-api-key
```

5. Start the backend server:
```bash
uvicorn server:app --reload
```

The backend will run on http://localhost:8000

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
# or
yarn install
```

3. Start the development server:
```bash
npm run dev
# or
yarn dev
```

The frontend will run on http://localhost:5173

## Usage

1. Open your browser and navigate to http://localhost:5173
2. You'll see a chat interface with a welcome message
3. Type your message in the input field and press Enter or click Send
4. The chatbot will process your message and respond accordingly

## Project Structure

```
chatbot/
├── frontend/
│   ├── src/
│   │   ├── Chatbot.tsx
│   │   └── chatbot.module.css
└── backend/
    ├── server.py
    ├── chat_service.py
    └── requirements.txt
```
