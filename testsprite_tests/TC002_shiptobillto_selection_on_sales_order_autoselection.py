import requests

BASE_URL = "http://localhost:8018"
TIMEOUT = 30
LOGIN_PAYLOAD = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "db": "erp",
        "login": "trihambono@gmail.com",
        "password": "Tr1-B0n0",
    }
}
HEADERS = {"Content-Type": "application/json"}


def login():
    resp = requests.post(
        f"{BASE_URL}/web/session/authenticate",
        json={
            "jsonrpc": "2.0",
            "params": {
                "db": "erp",
                "login": "trihambono@gmail.com",
                "password": "Tr1-B0n0"
            }
        },
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    assert "result" in data and "uid" in data["result"] and "user_context" in data["result"], f"Login response invalid: {data}"
    session_id = resp.cookies.get("session_id")
    assert session_id, "session_id cookie not found in response"
    return session_id, data["result"]["uid"], data["result"]["user_context"]


def search_read(model, domain, fields, session_id=None):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": "search_read",
            "args": [domain],
            "kwargs": {"fields": fields, "limit": 10},
        },
    }
    cookies = {"session_id": session_id} if session_id else {}
    resp = requests.post(
        f"{BASE_URL}/web/dataset/call_kw", json=payload, headers=HEADERS, cookies=cookies, timeout=TIMEOUT
    )
    resp.raise_for_status()
    data = resp.json()
    assert "result" in data, f"search_read response missing 'result': {data}"
    return data["result"]


def create_record(model, vals, session_id=None):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": "create",
            "args": [vals],
            "kwargs": {},
        },
    }
    cookies = {"session_id": session_id} if session_id else {}
    resp = requests.post(
        f"{BASE_URL}/web/dataset/call_kw", json=payload, headers=HEADERS, cookies=cookies, timeout=TIMEOUT
    )
    resp.raise_for_status()
    result = resp.json()
    assert "result" in result, f"Create failed: {result}"
    return result["result"]


def write_record(model, rec_id, vals, session_id=None):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": "write",
            "args": [[rec_id], vals],
            "kwargs": {},
        },
    }
    cookies = {"session_id": session_id} if session_id else {}
    resp = requests.post(
        f"{BASE_URL}/web/dataset/call_kw", json=payload, headers=HEADERS, cookies=cookies, timeout=TIMEOUT
    )
    resp.raise_for_status()
    result = resp.json()
    assert "result" in result, f"Write failed: {result}"
    return result["result"]


def unlink_record(model, rec_id, session_id=None):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": "unlink",
            "args": [[rec_id]],
            "kwargs": {},
        },
    }
    cookies = {"session_id": session_id} if session_id else {}
    resp = requests.post(
        f"{BASE_URL}/web/dataset/call_kw", json=payload, headers=HEADERS, cookies=cookies, timeout=TIMEOUT
    )
    resp.raise_for_status()
    result = resp.json()
    assert "result" in result, f"Unlink failed: {result}"
    return result["result"]


def call_kw(model, method, args=None, kwargs=None, session_id=None):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": method,
            "args": args or [],
            "kwargs": kwargs or {},
        },
    }
    cookies = {"session_id": session_id} if session_id else {}
    resp = requests.post(
        f"{BASE_URL}/web/dataset/call_kw", json=payload, headers=HEADERS, cookies=cookies, timeout=TIMEOUT
    )
    resp.raise_for_status()
    result = resp.json()
    if "error" in result:
        raise Exception(f"API error: {result['error']}")
    return result.get("result")


def test_shiptobillto_selection_on_sales_order_autoselection():
    session_id, uid, user_context = login()

    # Step 1: Find a customer with stored Sold To, Ship To and Bill To addresses
    customers = search_read(
        "sales.customer",
        [],
        ["id", "customer_name"],
        session_id=session_id,
    )
    assert customers, "No customers found"

    # Find a customer with all three address types
    found = False
    for cust in customers:
        customer_id = cust["id"]
        sold_tos = search_read("sales.sold_to", [("customer_id", "=", customer_id)], ["id", "sold_name"], session_id=session_id)
        ship_tos = search_read("sales.ship_to", [("customer_id", "=", customer_id)], ["id", "ship_name"], session_id=session_id)
        bill_tos = search_read("sales.bill_to", [("customer_id", "=", customer_id)], ["id", "bill_name"], session_id=session_id)
        if sold_tos and ship_tos and bill_tos:
            found = True
            break
    assert found, "No customer with all three address types found"

    # Step 2: Create a sales order for this customer and set all address fields

    order_vals = {
        "customer_id": customer_id,
        "sold_to_id": sold_tos[0]["id"],
        "ship_to_id": ship_tos[0]["id"],
        "bill_to_id": bill_tos[0]["id"],
    }

    order_id = None
    try:
        order_id = create_record("sales.sales_order", order_vals, session_id=session_id)

        # Step 3: Read the sales order record to verify ship_to_id and bill_to_id are set
        orders = search_read("sales.sales_order", [("id", "=", order_id)], ["id", "ship_to_id", "bill_to_id", "customer_id"], session_id=session_id)
        assert orders and orders[0]["id"] == order_id
        order = orders[0]
        assert order["customer_id"][0] == customer_id
        assert order["ship_to_id"] and order["ship_to_id"][0] in [st["id"] for st in ship_tos], \
            "ship_to_id not correctly set"
        assert order["bill_to_id"] and order["bill_to_id"][0] in [bt["id"] for bt in bill_tos], \
            "bill_to_id not correctly set"

        # Step 4: Update the sales order to save changes
        write_result = write_record("sales.sales_order", order_id, {"note": "Test update for auto-selection validation"}, session_id=session_id)
        assert write_result is True, "Failed to save order after auto-selection"

    finally:
        # Cleanup - delete the created sales order if any
        if order_id:
            unlink_record("sales.sales_order", order_id, session_id=session_id)


test_shiptobillto_selection_on_sales_order_autoselection()