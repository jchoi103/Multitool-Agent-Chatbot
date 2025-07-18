from typing import Annotated, Optional
import aiohttp
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from langchain.tools.base import StructuredTool
from product_search_tool import ProductSearchTool
import inspect
from langchain_core.tools import tool 
from cart_tools import CartTools
from order_tools import OrderTools
import asyncio
import os
import aiohttp
from dotenv import load_dotenv
from contextvars import ContextVar

load_dotenv()

PROXY_URL = os.getenv("PROXY_URL", "http://0.0.0.0:4000")
POSTGRES_CONNINFO = os.getenv("SUPABASE_POSTGRES_URL")
API_BASE_URL = "http://localhost:8000"

# context var for auth token
auth_token_var = ContextVar("auth_token", default=None)

class ChatService:
    def __init__(self):
        """Initialize the chat service with necessary configurations."""
        if not POSTGRES_CONNINFO:
            raise ValueError("need to set SUPABASE_POSTGRES_URL in .env file")

        print(f"Connecting to pooler")

        try:
            self.postgres_pool = ConnectionPool(
                conninfo=POSTGRES_CONNINFO,
                max_size=20,
                kwargs={"autocommit": True, "prepare_threshold": None},
            )

            with self.postgres_pool.connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    print("Connection to database succesful")
        except Exception as e:
            print(f"Error connecting to pooler: {e}")
            raise

        self.llm = ChatOpenAI(
            model_name="gpt-4o-mini",
        )

        self.product_search = ProductSearchTool()
        self.memory_savers = {}
        self.cart_tools = CartTools()
        self.order_tools = OrderTools()

        checkpointer = PostgresSaver(self.postgres_pool)
        try:
            checkpointer.setup()
        except Exception as e:
            print(f"Error: {e}")

    # helper function to preserve metadata of the original function
    def _preserve_metadata(self, original, wrapped):
        wrapped.__name__ = original.__name__
        wrapped.__doc__ = original.__doc__
        return wrapped

    # helper function to wrap cart tools with auth token
    def _wrap_auth(self, tool, auth_token: str):
        """Wraps a function to inject only auth_token."""
        def wrapped_tool():
            print(f"[AUTH ONLY WRAPPER] Calling {tool.__name__} with auth_token.")
            return tool(auth_token=auth_token)
        return self._preserve_metadata(tool, wrapped_tool)

    # helper function to wrap cart tools with auth token and other args
    def _wrap_auth_args(self, tool, auth_token: str):
        """Wraps a function to inject auth_token while preserving other arguments."""
        sig = inspect.signature(tool)

        def wrapped_tool(*args, **kwargs):
            # parse args if they are passed as a list of dicts - LLMs fall back to this format
            if "args" in kwargs:
                arg_list = kwargs.pop("args")
                if isinstance(arg_list, (list, tuple)) and len(arg_list) == 1 and isinstance(arg_list[0], dict):
                    kwargs.update(arg_list[0])

            # bind the arguments and inject auth_token
            bound = sig.bind_partial(*args, **kwargs)
            bound.arguments["auth_token"] = auth_token
            bound.apply_defaults()

            print(f"[TOOL CALL] {tool.__name__} with: {bound.arguments}")
            return tool(**bound.arguments)

        return self._preserve_metadata(tool, wrapped_tool)

    def _lookup_product_info(
        self,
        query: Annotated[str, "The product related question or search criteria"],
        weight: Annotated[Optional[float], "baseWeight of the product in pounds"] = None,
        height: Annotated[Optional[float], "Height of the product in inches"] = None,
        width: Annotated[Optional[float], "Width of the product in inches"] = None,
        length: Annotated[Optional[float], "Length of the product in inches"] = None,
        sku: Annotated[Optional[str], "Product SKU/part number"] = None,
    ) -> dict:
        """Tool for querying product information with optional dimensional specifications."""
        result = self.product_search.get_response(
            query=query,
            weight=weight,
            height=height,
            width=width,
            length=length,
            sku=sku,
        )
        return {"messages": [AIMessage(content=result)]}

    async def _get_product_url_by_name(self, name: str, token: str) -> dict:
        """Get product URL by name or SKU."""
        try:
            # First try to find by SKU if the input looks like a SKU
            if name.isalnum() and len(name) >= 6:
                result = self.product_search.get_response(query="", sku=name)
                if isinstance(result, str):
                    result = eval(result)
                if result["status"] == "SKU match found" and result["products"]:
                    product = result["products"][0]
                    if "Supabase_ID" in product:
                        url = f"http://localhost:5173/product/{product['Supabase_ID']}?variant={name}"
                        return {"messages": [AIMessage(content=url)]}
                # If SKU search failed and input is just a SKU (no spaces), return error
                if " " not in name:
                    return {"messages": [AIMessage(content="Sorry, no product with that name or SKU was found.")]}
            
            # If SKU search failed or input doesn't look like a SKU, try to find by name
            parts = name.split()
            potential_sku = parts[-1] if parts and parts[-1].isalnum() and len(parts[-1]) >= 6 else None
            product_name = " ".join(parts[:-1]) if potential_sku else name
            
            result = self.product_search.get_response(query=product_name)
            if isinstance(result, str):
                result = eval(result)
            
            if result["status"] != "No products found" and result["products"]:
                product = result["products"][0]
                if "Supabase_ID" in product:
                    if "SKU" in product:
                        url = f"http://localhost:5173/product/{product['Supabase_ID']}?variant={product['SKU']}"
                    else:
                        url = f"http://localhost:5173/product/{product['Supabase_ID']}"
                    return {"messages": [AIMessage(content=url)]}
            
            return {"messages": [AIMessage(content="Sorry, no product with that name or SKU was found.")]}

        except Exception as e:
            return {"messages": [AIMessage(content=f"Error retrieving product info: {str(e)}")]}

    def build_tools(self, auth_token: Optional[str] = None):
        tools = [
            StructuredTool.from_function(self._lookup_product_info),
            StructuredTool.from_function(self._get_product_url_by_name),
        ]

        if auth_token:
            tools += [
                self._wrap_auth(self.view_cart, auth_token),
                self._wrap_auth_args(self.add_to_cart, auth_token),
                self._wrap_auth_args(self.update_cart, auth_token),
                self._wrap_auth_args(self.remove_from_cart, auth_token),
                self._wrap_auth(self.clear_cart, auth_token),
                self._wrap_auth(self.create_order, auth_token),
                self._wrap_auth(self.get_orders, auth_token),
                self._wrap_auth_args(self.get_order_details, auth_token),
                self._wrap_auth_args(self.delete_order, auth_token),
                self._wrap_auth(self.clear_orders, auth_token),
            ]
        return tools

    # Cart and Order methods
    def view_cart(self, auth_token: Annotated[str, "User's authentication token"]) -> dict:
        """Tool for viewing the user's current shopping cart."""
        return self.cart_tools.view_cart(auth_token=auth_token)

    def add_to_cart(self, sku: Annotated[str, "Product SKU"], quantity: Annotated[int, "Quantity"] = 1, auth_token: Annotated[str, "User's authentication token"] = "") -> dict:
        """Tool for adding a product to the shopping cart."""
        return self.cart_tools.add_to_cart(sku, quantity, auth_token)

    def update_cart(self, sku: Annotated[str, "Product SKU"], quantity: Annotated[int, "New quantity"], auth_token: Annotated[str, "User's authentication token"] = "") -> dict:
        """Tool for updating product quantity in the shopping cart."""
        return self.cart_tools.update_cart(sku, quantity, auth_token)

    def remove_from_cart(self, sku: Annotated[str, "Product SKU"], auth_token: Annotated[str, "User's authentication token"] = "") -> dict:
        """Tool for removing a product from the shopping cart."""
        return self.cart_tools.remove_from_cart(sku, auth_token)

    def clear_cart(self, auth_token: Annotated[str, "User's authentication token"]) -> dict:
        """Tool for clearing all items from the shopping cart."""
        return self.cart_tools.clear_cart(auth_token)

    def create_order(self, auth_token: Annotated[str, "User's authentication token"]) -> dict:
        """Tool for creating a new order."""
        return self.order_tools.create_order(auth_token)

    def get_orders(self, auth_token: Annotated[str, "User's authentication token"]) -> dict:
        """Tool for retrieving the user's order history."""
        return self.order_tools.get_orders(auth_token)

    def get_order_details(self, order_id: Annotated[str, "Order ID"], auth_token: Annotated[str, "User's authentication token"] = "") -> dict:
        """Tool for retrieving order details."""
        return self.order_tools.get_order_details(order_id, auth_token)

    def delete_order(self, order_id: Annotated[str, "Order ID"], auth_token: Annotated[str, "User's authentication token"] = "") -> dict:
        """Tool for deleting an order."""
        return self.order_tools.delete_order(order_id, auth_token)
    
    def clear_orders(self, auth_token: Annotated[str, "User's authentication token"]) -> dict:
        """Tool for clearing all orders."""
        return self.order_tools.clear_orders(auth_token)

    async def get_response(self, query: str, session_id: str, auth_token=None) -> str:
        """Get a response for authenticated users."""
        print(f"[REACT_CHAT.PY] Received query for AUTHENTICATED USERS: {query} for session: {session_id}")
        tools = self.build_tools(auth_token)
        
        if session_id not in self.memory_savers:
            self.memory_savers[session_id] = PostgresSaver(self.postgres_pool)

        checkpointer = self.memory_savers[session_id]

        agent = create_react_agent(
            self.llm,
            tools=tools,
            prompt=(
                "You are an e-commerce chatbot. Help users search products, manage their cart, and view or update orders. "
                "Embed URLs when available. Do not answer unrelated questions. "
                "Do NOT ask for the user's auth token, because all requests already have it included."
            ),
            checkpointer=checkpointer,
        )

        config = {"configurable": {"thread_id": session_id}, "recursion_limit": 150}
        events = agent.stream(
            {"messages": [{"role": "user", "content": query}]},
            config,
            stream_mode="values",
        )

        result = ""
        for event in events:
            if "messages" in event:
                result = event["messages"][-1].content

        return result

    async def get_guest_response(self, query: str, session_id: str) -> str:
        """Get a response for guest users (unauthenticated)."""
        tools = self.build_tools()  # No auth token for guest users
        
        if session_id not in self.memory_savers:
            self.memory_savers[session_id] = PostgresSaver(self.postgres_pool)

        checkpointer = self.memory_savers[session_id]

        agent = create_react_agent(
            self.llm,
            tools=tools,
            prompt="You are an e-commerce chatbot. You can only help with product search for guest users. Politely explain that login is required for cart and order actions. Do not answer unrelated questions.",
            checkpointer=checkpointer,
        )

        config = {"configurable": {"thread_id": session_id}, "recursion_limit": 150}
        events = agent.stream(
            {"messages": [{"role": "user", "content": query}]},
            config,
            stream_mode="values",
        )

        result = ""
        for event in events:
            if "messages" in event:
                result = event["messages"][-1].content

        return result

    def cleanup(self):
        if hasattr(self, "postgres_pool"):
            self.postgres_pool.close()


async def main():
    chat = ChatService()
    try:
        while True:
            user_input = input("User: ")
            if user_input.lower() in ["exit", "quit"]:
                break

            await chat.get_response(
                user_input,
                "aaa",
                auth_token="eyJhbGciOiJIUzI1NiIsImtpZCI6IjNiVzVGcTJNMVN2dXVkQVAiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2NrZGRhYXdhd2x4anNpem9ib2h4LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiZGE0MmU1Ni01ZDQ5LTQ1MzQtOThlMy0wNmU5OTQxNzQzYjkiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzQ4ODI0NjMyLCJpYXQiOjE3NDg4MjEwMzIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzQ4ODIxMDMyfV0sInNlc3Npb25faWQiOiIzNjY2YTQ3MC05MzdmLTRlMGYtYmE1OS0zODU5MmVjODgyMjYiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.wSPSD5J3mD6D2fVGthhWngHzygYmY3b1LyMq9rqHQk0"
            )
    finally:
        chat.cleanup()


if __name__ == "__main__":
    asyncio.run(main())