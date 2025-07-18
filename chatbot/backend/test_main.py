import pytest
import os
from supabase import create_client, Client
from fastapi.testclient import TestClient
from main import app
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TEST_EMAIL = os.getenv("TEST_EMAIL")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@pytest.fixture(scope="module")
def access_token(supabase_client):
    auth_resp = supabase_client.auth.sign_in_with_password(
        {"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    return auth_resp.session.access_token


@pytest.fixture(scope="function")
def empty_cart(client, access_token):
    client.delete("/cart", headers={"Authorization": f"Bearer {access_token}"})
    return client, access_token


@pytest.fixture(scope="function")
def product_data(client):
    return client.get("/products").json()


@pytest.fixture(scope="function")
def no_orders(client, access_token):
    client.delete("/cart", headers={"Authorization": f"Bearer {access_token}"})
    client.delete("/orders", headers={"Authorization": f"Bearer {access_token}"})
    return client, access_token


def test_public_endpoint(client):
    resp = client.get("/public")
    assert resp.status_code == 200
    assert resp.json() == {"message": "Hello world"}


def test_private_endpoint(client, access_token):
    resp = client.get("/private", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    assert resp.json() == {"message": f"Logged in as {TEST_EMAIL}"}

    resp = client.get("/private")
    assert resp.status_code == 403
    assert resp.json() == {"detail": "Not authenticated"}

    resp = client.get("/private", headers={"Authorization": "Bearer invalid_token"})
    assert resp.status_code == 403
    assert resp.json() == {"detail": "Bad auth token"}


def test_get_products(client):
    resp = client.get("/products")
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, dict)
    assert len(data) > 0

    for id, info in data.items():
        assert isinstance(id, str)
        assert isinstance(info, dict)

        assert all(key in info for key in ["name", "description", "image", "variants"])
        assert all(
            isinstance(info[key], str) for key in ["name", "description", "image"]
        )

        variants = info["variants"]
        assert isinstance(variants, list)

        for variant in variants:
            assert isinstance(variant, dict)
            assert all(
                key in variant
                for key in ["sku", "price", "weight", "length", "width", "stock"]
            )
            assert isinstance(variant["sku"], str)
            assert all(
                isinstance(variant[key], (float, int, type(None)))
                for key in ["price", "weight", "length", "width", "stock"]
            )


def test_get_empty_cart(empty_cart):
    client, access_token = empty_cart
    resp = client.get("/cart", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    assert resp.json() == {}


def test_add_item_to_cart(empty_cart, product_data):
    client, access_token = empty_cart
    id, item = product_data.popitem()
    var = item["variants"][0]
    sku = var["sku"]

    resp = client.post(
        f"/cart/{sku}", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert resp.status_code == 200
    assert resp.json() == {
        sku: {
            "name": item["name"],
            "unit_price": var["price"],
            "quantity": 1,
            "product_id": id,
        }
    }


def test_inc_item_qty(empty_cart, product_data):
    client, access_token = empty_cart
    _, item = product_data.popitem()
    var = item["variants"][0]
    sku = var["sku"]

    resp1 = client.post(
        f"/cart/{sku}", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp1.status_code == 200
    assert resp1.json()[sku]["quantity"] == 1

    resp2 = client.post(
        f"/cart/{sku}", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp2.status_code == 200
    assert resp2.json()[sku]["quantity"] == 2


def test_add_multiple(empty_cart, product_data):
    client, access_token = empty_cart
    items = list(product_data.items())

    _, item1 = items[0]
    var1 = item1["variants"][0]
    sku1 = var1["sku"]
    client.post(f"/cart/{sku1}", headers={"Authorization": f"Bearer {access_token}"})

    _, item2 = items[1]
    var2 = item2["variants"][0]
    sku2 = var2["sku"]
    resp = client.post(
        f"/cart/{sku2}", headers={"Authorization": f"Bearer {access_token}"}
    )

    cart_data = resp.json()
    assert resp.status_code == 200
    assert len(cart_data) == 2
    assert sku1 in cart_data
    assert sku2 in cart_data


def test_update_qty(empty_cart, product_data):
    client, access_token = empty_cart
    _, item = product_data.popitem()
    var = item["variants"][0]
    sku = var["sku"]

    client.post(f"/cart/{sku}", headers={"Authorization": f"Bearer {access_token}"})
    resp = client.patch(
        f"/cart/{sku}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"quantity": 10},
    )
    assert resp.status_code == 200
    assert resp.json()[sku]["quantity"] == 10


def test_patch_insert(empty_cart, product_data):
    client, access_token = empty_cart
    _, item = list(product_data.items())[2]
    var = item["variants"][0]
    sku = var["sku"]

    resp = client.patch(
        f"/cart/{sku}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"quantity": 3},
    )
    assert resp.status_code == 200
    assert resp.json()[sku]["quantity"] == 3


def test_remove_zero_qty(empty_cart, product_data):
    client, access_token = empty_cart
    _, item = product_data.popitem()
    var = item["variants"][0]
    sku = var["sku"]

    client.post(f"/cart/{sku}", headers={"Authorization": f"Bearer {access_token}"})

    resp = client.patch(
        f"/cart/{sku}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"quantity": 0},
    )
    assert resp.status_code == 200
    assert sku not in resp.json()


def test_clear_cart(empty_cart, product_data):
    client, access_token = empty_cart
    _, item = product_data.popitem()
    var = item["variants"][0]
    sku = var["sku"]

    client.post(f"/cart/{sku}", headers={"Authorization": f"Bearer {access_token}"})
    resp = client.delete("/cart", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    assert resp.json() == {}


def test_empty_order(no_orders):
    client, access_token = no_orders
    resp = client.post(f"/orders", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Cart is empty."


def test_no_orders(no_orders):
    client, access_token = no_orders
    resp = client.get(f"/orders", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_order_everything(no_orders, product_data):
    client, access_token = no_orders
    _, item = product_data.popitem()
    var = item["variants"][0]
    sku = var["sku"]

    cart = client.post(
        f"/cart/{sku}", headers={"Authorization": f"Bearer {access_token}"}
    ).json()
    resp = client.post(f"/orders", headers={"Authorization": f"Bearer {access_token}"})

    assert resp.status_code == 200
    assert "order_id" in resp.json()
    order_id = resp.json()["order_id"]

    resp = client.get(f"/orders", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    assert resp.json()[0]["id"] == order_id

    resp = client.get(
        f"/orders/{order_id}", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp.status_code == 200
    order = resp.json()

    assert order["order_id"] == order_id
    assert order["contents"] == cart

    resp = client.delete(
        f"/orders/{order_id}", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp.status_code == 200

    resp = client.get(
        f"/orders/{order_id}", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp.status_code == 404
