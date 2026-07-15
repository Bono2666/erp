import requests

BASE_URL = "http://localhost:8018"
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 30

LOGIN_PAYLOAD = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "db": "erp",
        "login": "trihambono@gmail.com",
        "password": "Tr1-B0n0"
    },
    "id": 1,
}


def login():
    url = f"{BASE_URL}/web/session/authenticate"
    response = requests.post(url, json=LOGIN_PAYLOAD, timeout=TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    session_info = data.get("result")
    assert session_info and "uid" in session_info, "Login failed, no uid in response"
    # Extract session_id from cookies
    cookies = response.cookies
    session_id = cookies.get("session_id")
    assert session_id, "Login failed, no session_id cookie in response"
    return session_id, session_info["uid"]


def call_kw(session_id, model, method, args=None, kwargs=None, context=None):
    url = f"{BASE_URL}/web/dataset/call_kw"
    headers = HEADERS.copy()
    headers["Cookie"] = f"session_id={session_id}"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": method,
            "args": args if args is not None else [],
            "kwargs": kwargs if kwargs is not None else {},
            "context": context if context is not None else {},
        },
        "id": 1,
    }
    response = requests.post(url, json=payload, timeout=TIMEOUT, headers=headers)
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise Exception(f"API error: {data['error']}")
    return data.get("result")


def create_customer(session_id, name):
    # Create sales.customer directly with customer_name and required fields
    customer_vals = {
        "customer_name": name,
        "cust_category": 1,  # Required field - Corporate / Enterprise (B2B)
        "email": f"test_{name.lower().replace(' ', '_')}@example.com",
    }
    customer_id = call_kw(session_id, "sales.customer", "create", args=[customer_vals])
    assert isinstance(customer_id, int), "Failed to create customer"
    return customer_id


def create_address(session_id, model, vals):
    rec_id = call_kw(session_id, model, "create", args=[vals])
    assert isinstance(rec_id, int), f"Failed to create record in {model}"
    return rec_id


def delete_record(session_id, model, record_id):
    call_kw(session_id, model, "unlink", args=[[record_id]])


def test_shiptobillto_selection_on_sales_order_manual_selection_and_validation():
    session_id, user_id = login()

    # Step 1: Create a new customer with no associated ship_to or bill_to addresses
    customer_name = "TC003 Test Customer No Addresses"
    customer_id = create_customer(session_id, customer_name)

    try:
        # Confirm no Ship To or Bill To addresses exist for this customer
        domain = [["customer_id", "=", customer_id]]

        ship_to_ids = call_kw(session_id, "sales.ship_to", "search", args=[domain])
        bill_to_ids = call_kw(session_id, "sales.bill_to", "search", args=[domain])
        assert len(ship_to_ids) == 0, "Customer unexpectedly has Ship To addresses"
        assert len(bill_to_ids) == 0, "Customer unexpectedly has Bill To addresses"

        # Step 2: Create sales order without matching Ship To / Bill To - fields should be empty
        order_vals = {
            "customer_id": customer_id,
        }
        sales_order_id = call_kw(session_id, "sales.sales_order", "create", args=[order_vals])
        assert isinstance(sales_order_id, int), "Failed to create sales order"

        # Read sales order to verify ship_to_id and bill_to_id are empty or falsy
        sales_order = call_kw(session_id, "sales.sales_order", "read", args=[[sales_order_id], ["ship_to_id", "bill_to_id"]])
        assert len(sales_order) == 1, "Sales order read failed"
        so = sales_order[0]
        assert not so.get("ship_to_id"), "Expected empty ship_to_id on new SO with no addresses"
        assert not so.get("bill_to_id"), "Expected empty bill_to_id on new SO with no addresses"

        # Step 3: Create valid Ship To and Bill To addresses for this customer manually
        ship_to_vals = {
            "customer_id": customer_id,
            "ship_name": "Valid Ship To Address",
            "address": "123 Valid Ship To St., ShipCity"
        }
        ship_to_id = create_address(session_id, "sales.ship_to", ship_to_vals)

        bill_to_vals = {
            "customer_id": customer_id,
            "bill_name": "Valid Bill To Address",
            "address": "456 Valid Bill To Ave., BillTown"
        }
        bill_to_id = create_address(session_id, "sales.bill_to", bill_to_vals)

        # Step 4: Manually update sales order with valid ship_to_id and bill_to_id - should succeed
        update_vals = {
            "ship_to_id": ship_to_id,
            "bill_to_id": bill_to_id,
        }
        res = call_kw(session_id, "sales.sales_order", "write", args=[[sales_order_id], update_vals])
        assert res is True, "Failed to update sales order with valid ship_to_id and bill_to_id"

        # Verify update persisted
        sales_order_updated = call_kw(session_id, "sales.sales_order", "read", args=[[sales_order_id], ["ship_to_id", "bill_to_id"]])
        so_updated = sales_order_updated[0]
        assert so_updated.get("ship_to_id") and so_updated["ship_to_id"][0] == ship_to_id
        assert so_updated.get("bill_to_id") and so_updated["bill_to_id"][0] == bill_to_id

        # Step 5: Attempt to set invalid (non-existent) ship_to_id and bill_to_id - expect validation error
        invalid_id = 99999999  # Assumed invalid ID

        try:
            call_kw(session_id, "sales.sales_order", "write", args=[[sales_order_id], {"ship_to_id": invalid_id}])
            assert False, "Updating with invalid ship_to_id should have failed but did not"
        except Exception as e:
            assert "Invalid" in str(e) or "not found" in str(e) or "relation" in str(e) or "error" in str(e)

        try:
            call_kw(session_id, "sales.sales_order", "write", args=[[sales_order_id], {"bill_to_id": invalid_id}])
            assert False, "Updating with invalid bill_to_id should have failed but did not"
        except Exception as e:
            assert "Invalid" in str(e) or "not found" in str(e) or "relation" in str(e) or "error" in str(e)

    finally:
        # Cleanup in reverse order
        try:
            if 'sales_order_id' in locals():
                delete_record(session_id, "sales.sales_order", sales_order_id)
        except Exception:
            pass
        try:
            if 'ship_to_id' in locals():
                delete_record(session_id, "sales.ship_to", ship_to_id)
        except Exception:
            pass
        try:
            if 'bill_to_id' in locals():
                delete_record(session_id, "sales.bill_to", bill_to_id)
        except Exception:
            pass
        try:
            delete_record(session_id, "sales.customer", customer_id)
        except Exception:
            pass


test_shiptobillto_selection_on_sales_order_manual_selection_and_validation()
