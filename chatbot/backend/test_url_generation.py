import json
from react_chat import ChatService
import asyncio
from server import app
from fastapi.testclient import TestClient
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from unittest.mock import patch, MagicMock
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
MOCK_PRODUCTS = {
    "230025": {
        "Supabase_ID": "1",
        "SKU": "230025",
        "Name": "Quadruplex Aluminum Cable"
    },
    "200010": {
        "Supabase_ID": "2",
        "SKU": "200010",
        "Name": "Shielded Motor Drop Cable"
    }
}
client = TestClient(app)
chat_service = ChatService()

async def get_auth_token():
    """Get authentication token by signing in"""
    try:
        email = os.getenv("TEST_USER_EMAIL")
        password = os.getenv("TEST_USER_PASSWORD")
        
        if not email or not password:
            raise ValueError("TEST_USER_EMAIL and TEST_USER_PASSWORD must be set in .env file")
        
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.session:
            return response.session.access_token
        else:
            raise Exception("Failed to get authentication token")
    except Exception as e:
        print(f"Authentication error: {e}")
        return None

def mock_get_response(self, query="", sku=None, **kwargs):
    """Mock implementation of ProductSearchTool.get_response"""
    if sku:
        if sku in MOCK_PRODUCTS:
            return {
                "status": "SKU match found",
                "products": [MOCK_PRODUCTS[sku]]
            }
        return {"status": "No products found", "products": []}
    for product in MOCK_PRODUCTS.values():
        if query.lower() in product["Name"].lower():
            return {
                "status": "Product found",
                "products": [product]
            }
    return {"status": "No products found", "products": []}

async def test_url_generation():
    auth_token = await get_auth_token()
    if not auth_token:
        print("Failed to authenticate. Please check your credentials.")
        return
    test_cases = [
        {
            "input": "230025",
            "expected": "http://localhost:5173/product/1?variant=230025",
            "description": "Valid SKU should return exact variant URL"
        },
        {
            "input": "200010",
            "expected": "http://localhost:5173/product/2?variant=200010",
            "description": "Another valid SKU should return its variant URL"
        },
        {
            "input": "Quadruplex Aluminum Cable 999999",
            "expected": "http://localhost:5173/product/1?variant=230025",
            "description": "Invalid SKU with valid product name should default to first variant"
        },
        {
            "input": "Aluminum Cable 999999",
            "expected": "http://localhost:5173/product/1?variant=230025",
            "description": "Invalid SKU with partial product name should default to first variant"
        },
        {
            "input": "999999",
            "expected": "Sorry, no product with that name or SKU was found.",
            "description": "Invalid SKU without product name should return error"
        },
        {
            "input": "Quadruplex Aluminum Cable",
            "expected": "http://localhost:5173/product/1?variant=230025",
            "description": "Product name without variant should use first variant"
        },
        {
            "input": "Aluminum Cable",
            "expected": "http://localhost:5173/product/1?variant=230025",
            "description": "Partial product name should use first variant"
        }
    ]
    print("Testing URL Generation with Variant Handling\n")
    print("-" * 70)
    with patch('product_search_tool.ProductSearchTool.get_response', mock_get_response):
        for test in test_cases:
            print(f"\nTest: {test['description']}")
            print(f"Input: {test['input']}")
            print(f"Expected URL: {test['expected']}")
            try:
                result = await chat_service._get_product_url_by_name(test['input'], auth_token)
                actual_response = result["messages"][0].content
                print(f"Actual Response: {actual_response}")
                if actual_response.startswith("http://"):
                    actual_variant = actual_response.split("variant=")[-1] if "variant=" in actual_response else None
                    expected_variant = test['expected'].split("variant=")[-1] if "variant=" in test['expected'] else None
                    if actual_variant == expected_variant:
                        print("Test PASSED: Variant matches expected")
                    elif actual_variant == "230025" and "999999" in test['input'] and "Aluminum" in test['input']:
                        print("Test PASSED: Defaulted to first variant for invalid SKU with valid product name")
                    else:
                        print("Test FAILED: Unexpected variant in URL")
                else:
                    if actual_response == test['expected']:
                        print("Test PASSED: Expected error message received")
                    else:
                        print("Test FAILED: Unexpected error message")
            except Exception as e:
                print(f"Test Error: {str(e)}")
            
            print("-" * 70)
if __name__ == "__main__":
    asyncio.run(test_url_generation()) 