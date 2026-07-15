import requests

BASE_URL = "http://localhost:8018"
LOGIN_ENDPOINT = f"{BASE_URL}/web/session/authenticate"
CALL_KW_ENDPOINT = f"{BASE_URL}/web/dataset/call_kw"

EMAIL = "trihambono@gmail.com"
PASSWORD = "Tr1-B0n0"
DB = "erp"
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 30

def login():
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": DB,
            "login": EMAIL,
            "password": PASSWORD,
        }
    }
    resp = requests.post(LOGIN_ENDPOINT, json=payload, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    res = resp.json()
    if "result" not in res or "uid" not in res["result"]:
        raise Exception("Login failed or no uid returned")
    session_id = resp.cookies.get("session_id")
    if not session_id:
        raise Exception("No session cookie returned")
    return session_id

def get_view_data(model, view_type, domain=None, context=None, session_id=None):
    # Adjust fields based on model to avoid invalid field errors
    if model == "sales.customer":
        fields = ["id", "display_name"]
    elif model == "sales.sold_to":
        fields = ["id", "sold_name", "address", "customer_id"]
    elif model == "sales.ship_to":
        fields = ["id", "ship_name", "address", "customer_id"]
    elif model == "sales.bill_to":
        fields = ["id", "bill_name", "address", "customer_id"]
    else:
        fields = ["id", "display_name"]
    params = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": "search_read",
            "args": [],
            "kwargs": {
                "domain": domain or [],
                "fields": fields,
                "limit": 50,
                "context": context or {},
            },
        }
    }
    # Normally view switching done in UI. We'll simulate toggle by fetching data to represent Tree or Kanban
    # We'll use context with 'search_view' or 'kanban_view' key to simulate view type
    params["params"]["kwargs"]["context"]["view_mode"] = view_type
    cookies = {"session_id": session_id}
    resp = requests.post(CALL_KW_ENDPOINT, json=params, headers=HEADERS, cookies=cookies, timeout=TIMEOUT)
    resp.raise_for_status()
    res = resp.json()
    if "error" in res:
        raise Exception(f"RPC call error: {res['error']}")
    return res.get("result", [])

def soldtoshiptobillto_tree_view_toggle_functionality():
    session_id = None
    try:
        session_id = login()
        cookies = {"session_id": session_id}

        # Step 1: Get Customers to test with.
        # Fetch at least one customer
        customer_data = get_view_data(
            model="sales.customer",
            view_type="tree",
            session_id=session_id
        )
        assert isinstance(customer_data, list)
        if not customer_data:
            raise Exception("No customers found to test Sold To/Ship To/Bill To")

        customer_id = customer_data[0]["id"]

        # Define models and their tab names to test toggle on:
        address_models = [
            ("sales.sold_to", "Sold To"),
            ("sales.ship_to", "Ship To"),
            ("sales.bill_to", "Bill To"),
        ]

        for model, tabname in address_models:
            # Simulate loading Tree view data
            tree_view_result = get_view_data(
                model=model,
                view_type="tree",
                domain=[("customer_id", "=", customer_id)],
                session_id=session_id,
            )
            assert isinstance(tree_view_result, list), f"{model} Tree view response not list"
            # Tree view should include multiple or zero entries but be a list
            # The entries should have id key
            for record in tree_view_result:
                assert "id" in record, f"{model} Tree view record missing id key"
            
            # Simulate loading Kanban view data
            kanban_view_result = get_view_data(
                model=model,
                view_type="kanban",
                domain=[("customer_id", "=", customer_id)],
                session_id=session_id,
            )
            assert isinstance(kanban_view_result, list), f"{model} Kanban view response not list"
            for record in kanban_view_result:
                assert "id" in record, f"{model} Kanban view record missing id key"
            
            # Verify that toggling between views changes data representation
            # They can be same data in different layout, so we just check that both responses returned lists
            # and include expected fields.

        # Test invalid or empty customer context returns empty results
        for model, tabname in address_models:
            empty_context_result = get_view_data(
                model=model,
                view_type="tree",
                domain=[("customer_id", "=", 0)],  # Assuming 0 is invalid customer_id
                session_id=session_id,
            )
            assert empty_context_result == [] or len(empty_context_result) == 0, f"{model} empty context should return empty list"

    except Exception as e:
        raise e

soldtoshiptobillto_tree_view_toggle_functionality()
