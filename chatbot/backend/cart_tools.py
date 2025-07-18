import requests
from langchain_core.messages import AIMessage

BASE_URL = "http://127.0.0.1:8000"

USER_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjNiVzVGcTJNMVN2dXVkQVAiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2NrZGRhYXdhd2x4anNpem9ib2h4LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiZGE0MmU1Ni01ZDQ5LTQ1MzQtOThlMy0wNmU5OTQxNzQzYjkiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzQ4NjY4MjU1LCJpYXQiOjE3NDg2NjQ2NTUsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzQ4NjY0NjU1fV0sInNlc3Npb25faWQiOiIxZWI5Nzg2Ni0yMTk5LTRkZjItODMwMS0xYWNhNTc4OThhNGEiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ._xvvVN77niX0edYPltZ-8pnIeHO63GzGt4v0ODCJDsA"
class CartTools:
    def __init__(self):
        pass

    def request(self, method: str, path: str, auth_token: str, quantity: int = None):
        """Generic request handler for cart operations."""
        try:
            headers = {"Authorization": f"Bearer {auth_token}"}
            url = f"{BASE_URL}{path}"
            if quantity is not None:
                url += f"?quantity={quantity}"

            response = requests.request(method, url, headers=headers)

            if response.status_code == 200:
                return {"messages": [AIMessage(content=str({"status": "success", "cart": response.json()}))]}
            else:
                return {"messages": [AIMessage(content=str({
                    "status": "error",
                    "message": response.text
                }))]}
        except Exception as e:
            return {"messages": [AIMessage(content=str({"status": "error", "message": str(e)}))]}

    def validate_auth_token(self, auth_token):
        """Validate the provided auth token."""
        if not auth_token:
            print("[ERROR - CART_TOOLS] No auth token provided, returning without performing any cart operations.")
            return 
        else:
            print("[SUCCESS - CART_TOOLS] Using provided auth token for cart operations.")
        return auth_token
    
    def view_cart(self, auth_token):
        """View the current user's cart."""
        auth_token = self.validate_auth_token(auth_token)
        if not auth_token:  # testing purposes only
            return {"messages": [AIMessage(content="No auth token provided.")]}
        
        print(f"[CART_TOOLS] Calling GET /cart endpoint with auth token: {auth_token[:8]}")
        return self.request("GET", "/cart", auth_token)

    def add_to_cart(self, sku, quantity, auth_token):
        """Add an item to the cart."""
        print(f"[CART_TOOLS] Calling POST /cart endpoint with {quantity},  {sku}, and {auth_token[:8]}")
        auth_token = self.validate_auth_token(auth_token)
        if not auth_token:  # testing purposes only
            return {"messages": [AIMessage(content="No auth token provided.")]}
        
        result = self.request("POST", f"/cart/{sku}", auth_token)
        if quantity > 1:
            return self.update_cart(sku, quantity, auth_token)
        return result

    def update_cart(self, sku, quantity, auth_token):
        """Update the quantity of an item in the cart."""
        return self.request("PATCH", f"/cart/{sku}", auth_token, quantity)

    def remove_from_cart(self, sku, auth_token):
        """Remove an item from the cart."""
        return self.request("DELETE", f"/cart/{sku}", auth_token)

    def clear_cart(self, auth_token):
        """Clear the entire cart."""
        return self.request("DELETE", "/cart", auth_token)
    
    
if __name__ == "__main__":
    cart_tools = CartTools()

    print("=== Testing view_cart ===")
    response = cart_tools.view_cart(USER_TOKEN)
    print(response)

    # print("\n=== Testing add_to_cart ===")
    # sku = "200060"
    # quantity = 2
    # response = cart_tools.add_to_cart(sku, quantity, USER_TOKEN)
    # print(response)

    # print("\n=== Testing update_cart ===")
    # response = cart_tools.update_cart(sku, 5, USER_TOKEN)
    # print(response)

    # print("\n=== Testing remove_from_cart ===")
    # response = cart_tools.remove_from_cart(sku, USER_TOKEN)
    # print(response)

    # print("\n=== Testing clear_cart ===")
    # response = cart_tools.clear_cart(USER_TOKEN)
    # print(response)

