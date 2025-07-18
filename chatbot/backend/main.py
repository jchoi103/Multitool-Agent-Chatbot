import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
import uvicorn

load_dotenv()
app = FastAPI()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    print(f"[MAIN.PY] Raw Authorization header: {creds.credentials}")
    try:
        response = supabase.auth.get_user(creds.credentials)
        print(f"[MAIN.PY] User response: {response.user}")
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authenticated",
            )
        return response.user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bad auth token",
        )

@app.get("/config/supabase")
async def get_supabase_config():
    return {"url": SUPABASE_URL, "anon_key": SUPABASE_KEY}

@app.get("/public")
async def public_endpoint():
    return {"message": "Hello world"}

@app.get("/private")
async def private_endpoint(user=Depends(get_current_user)):
    return {"message": f"Logged in as {user.email}"}

@app.get("/products")
async def get_products():
    response = supabase.rpc("get_all_products").execute()
    return response.data

@app.get("/cart")
async def get_cart(user=Depends(get_current_user)):
    print(f"[MAIN.PY] User ID: {user.id}")
    response = supabase.rpc("get_cart", {"p_user_id": user.id}).execute()
    return response.data

@app.post("/cart/{sku}")
async def add_to_cart(sku: str, user=Depends(get_current_user)):
    response = supabase.rpc(
        "add_to_cart", {"p_user_id": user.id, "p_sku": sku}
    ).execute()
    if hasattr(response, "error") and response.error is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=response.error.message
        )
    return response.data

@app.patch("/cart/{sku}")
async def update_cart(sku: str, quantity: int, user=Depends(get_current_user)):
    response = supabase.rpc(
        "update_cart_item", {"p_user_id": user.id, "p_sku": sku, "p_quantity": quantity}
    ).execute()
    if hasattr(response, "error") and response.error is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=response.error.message
        )
    return response.data

@app.delete("/cart/{sku}")
async def delete_from_cart(sku: str, user=Depends(get_current_user)):
    response = supabase.rpc(
        "update_cart_item", {"p_user_id": user.id, "p_sku": sku, "p_quantity": 0}
    ).execute()
    if hasattr(response, "error") and response.error is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=response.error.message
        )
    return response.data

@app.delete("/cart")
async def clear_cart(user=Depends(get_current_user)):
    response = supabase.rpc("clear_cart", {"p_user_id": user.id}).execute()
    if hasattr(response, "error") and response.error is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=response.error.message
        )
    return response.data

@app.post("/orders")
async def create_order(user=Depends(get_current_user)):
    response = supabase.rpc("create_order", {"p_user_id": user.id}).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty."
        )

    if hasattr(response, "error") and response.error is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=response.error.message
        )
    return response.data

@app.get("/orders")
async def get_order_history(user=Depends(get_current_user)):
    response = (
        supabase.table("orders")
        .select("*")
        .eq("user_id", user.id)
        .order("placed_at")
        .execute()
    )
    return response.data

@app.get("/orders/{id}")
async def get_order_detail(id: str, user=Depends(get_current_user)):
    response = supabase.rpc("get_order", {"p_order_id": id}).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    if user.id != response.data["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This order does not belong to you.",
        )
    return response.data

@app.delete("/orders/{id}")
async def delete_order(id: str, user=Depends(get_current_user)):
    check_response = supabase.table("orders").select("user_id").eq("id", id).execute()

    if not check_response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    if user.id != check_response.data[0]["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This order does not belong to you",
        )

    response = supabase.table("orders").delete().eq("id", id).execute()
    return response.data

@app.delete("/orders")
async def clear_orders(user=Depends(get_current_user)):
    response = supabase.table("orders").delete().eq("user_id", user.id).execute()
    return response.data

@app.get("/products/search")
async def search_product(name: str):
    response = supabase.table("products").select("id", "name").ilike("name", f"%{name}%").execute()
    return response.data

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)