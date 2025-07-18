import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from react_chat import ChatService
import atexit
from supabase import create_client, Client
import uvicorn

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
chat_service = ChatService()
security = HTTPBearer()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@atexit.register
def cleanup():
    chat_service.cleanup()

class ChatRequest(BaseModel):
    message: str
    session_id: str

async def get_optional_token(authorization: str = None):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        try:
            if supabase.auth.get_user(token).user:
                return token
        except Exception as e:
            # pass
            return None
    return None

@app.post("/chat")
async def chat(request: ChatRequest, authorization: str = Header(None)):
    #print(f"[SERVER.PY] Raw Authorization header: {authorization}")
    token = await get_optional_token(authorization)

    try:
        print(f"[SERVER.PY] Authorization token: {token}")
        if not request.message or not request.session_id:
            raise HTTPException(status_code=400, detail="Message and session_id are required.")
        #print(f"[SERVER.PY] Received message: {request.message} for session: {request.session_id}")
        
        if token:
            print("[SERVER.PY] Valid token provided, using authenticated mode.")
            response = await chat_service.get_response(request.message, request.session_id, auth_token=token)
        else:
            print("[SERVER.PY] No valid token provided, using guest mode.")
            response = await chat_service.get_guest_response(request.message, request.session_id)
        return {"response": response}

    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Something went wrong.")

class EndSessionRequest(BaseModel):
    session_id: str

@app.delete("/chat/end_session")
async def end_session(request: EndSessionRequest):
    if request.session_id in chat_service.memory_savers:
        del chat_service.memory_savers[request.session_id]
        return {"message": "Session ended"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.get("/chat")
async def chat_root():
    return {"message": "Chat API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
