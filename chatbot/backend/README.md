# Chatbot Backend Server

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

To run the server, use the following command:
```bash
uvicorn server:app --reload
```

The server will start at `http://localhost:8000`

