import requests
from langchain_core.messages import AIMessage

BASE_URL = "http://127.0.0.1:8000"

class OrderTools:
    def __init__(self):
        pass

    def request(self, method: str, path: str, auth_token: str, data=None):
        """Generic request handler for order operations."""
        try:
            headers = {"Authorization": f"Bearer {auth_token}"}
            url = f"{BASE_URL}{path}"

            response = requests.request(method, url, headers=headers, json=data)

            if response.status_code == 200:
                return {"messages": [AIMessage(content=str({"status": "success", "data": response.json()}))]}
            elif response.status_code == 400:
                return {"messages": [AIMessage(content=str({"status": "error", "message": "Bad request or cart empty"}))]}
            elif response.status_code == 403:
                return {"messages": [AIMessage(content=str({"status": "error", "message": "Unauthorized access"}))]}
            elif response.status_code == 404:
                return {"messages": [AIMessage(content=str({"status": "error", "message": "Not found"}))]}
            else:
                return {"messages": [AIMessage(content=str({"status": "error", "message": response.text}))]}
        except Exception as e:
            return {"messages": [AIMessage(content=str({"status": "error", "message": str(e)}))]}

    def create_order(self, auth_token):
        """Create a new order for the current user."""
        return self.request("POST", "/orders", auth_token)

    def get_orders(self, auth_token):
        """Retrieve all orders for the current user."""
        return self.request("GET", "/orders", auth_token)

    def get_order_details(self, order_id, auth_token):
        """Retrieve details of a specific order by its ID."""
        return self.request("GET", f"/orders/{order_id}", auth_token)

    def delete_order(self, order_id, auth_token):
        """Delete a specific order by its ID."""
        return self.request("DELETE", f"/orders/{order_id}", auth_token)

    def clear_orders(self, auth_token):
        """Clear all orders for the current user."""
        return self.request("DELETE", "/orders", auth_token)
