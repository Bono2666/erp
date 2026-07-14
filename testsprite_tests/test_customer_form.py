import requests
import uuid
import json

BASE_URL = "http://localhost:8018"
TIMEOUT = 30
DB_NAME = "erp"


def run_test():
    session = requests.Session()
    headers = {"Content-Type": "application/json"}

    # Authenticate
    auth_payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": DB_NAME,
            "login": "trihambono@gmail.com",
            "password": "Tr1-B0n0",
            "context": {}
        },
        "id": int(uuid.uuid4().int % 100000)
    }
    auth_resp = session.post(f"{BASE_URL}/web/session/authenticate", json=auth_payload, headers=headers, timeout=TIMEOUT)
    assert auth_resp.status_code == 200, f"Auth failed: {auth_resp.text}"
    auth_result = auth_resp.json()
    assert "result" in auth_result and "uid" in auth_result["result"], f"Auth error: {auth_result}"
    print("[PASS] Authentication successful")

    def call_kw(model, method, args=None, kwargs=None):
        args = args or []
        kwargs = kwargs or {}
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"model": model, "method": method, "args": args, "kwargs": kwargs},
            "id": int(uuid.uuid4().int % 100000),
        }
        resp = session.post(f"{BASE_URL}/web/dataset/call_kw", json=payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        result = resp.json()
        if "error" in result:
            raise Exception(f"Error {model}.{method}: {result['error']}")
        return result.get("result")

    def search_read(model, domain=None, fields=None):
        domain = domain or []
        fields = fields or []
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"model": model, "method": "search_read", "args": [domain], "kwargs": {"fields": fields}},
            "id": int(uuid.uuid4().int % 100000),
        }
        resp = session.post(f"{BASE_URL}/web/dataset/call_kw", json=payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("result", [])

    # ============================================================
    # TEST 1: Verify new fields exist on sales.customer model
    # ============================================================
    print("\n--- TEST 1: Verify new fields on sales.customer ---")
    fields_info = call_kw("sales.customer", "fields_get", [], {"attributes": ["string", "type"]})
    new_fields = ["tags", "pkp", "cust_sub_category", "sold_to_ids", "ship_to_ids", "bill_to_ids"]
    for f in new_fields:
        assert f in fields_info, f"Field '{f}' not found in sales.customer"
        print(f"  [PASS] Field '{f}' exists (type: {fields_info[f]['type']})")

    # ============================================================
    # TEST 2: Verify new models exist
    # ============================================================
    print("\n--- TEST 2: Verify new models exist ---")
    for model in ["sales.sold_to", "sales.bill_to", "sales.cust_sub_category"]:
        result = call_kw(model, "search", [[]])
        assert isinstance(result, list), f"Model {model} not accessible"
        print(f"  [PASS] Model '{model}' is accessible")

    # ============================================================
    # TEST 3: Create Customer Category (if not exists)
    # ============================================================
    print("\n--- TEST 3: Create Customer Category ---")
    cats = search_read("sales.cust_category", [], ["category_id", "category_name"])
    if cats:
        cat_id = cats[0]["id"]
        print(f"  Using existing category: {cats[0]['category_name']} (id={cat_id})")
    else:
        cat_id = call_kw("sales.cust_category", "create", [{"category_name": "Test Category"}])
        print(f"  Created category id={cat_id}")

    # ============================================================
    # TEST 4: Create Customer Sub Category
    # ============================================================
    print("\n--- TEST 4: Create Customer Sub Category ---")
    sub_cats = search_read("sales.cust_sub_category", [], ["sub_category_id", "sub_category_name"])
    if sub_cats:
        sub_cat_id = sub_cats[0]["id"]
        print(f"  Using existing sub category: {sub_cats[0]['sub_category_name']} (id={sub_cat_id})")
    else:
        sub_cat_id = call_kw("sales.cust_sub_category", "create", [{
            "sub_category_name": "Test Sub Category",
            "category_ref": cat_id
        }])
        print(f"  Created sub category id={sub_cat_id}")

    # ============================================================
    # TEST 5: Create Customer with all new fields
    # ============================================================
    print("\n--- TEST 5: Create Customer with new fields ---")
    customer_vals = {
        "customer_name": f"Test Customer {uuid.uuid4().hex[:6]}",
        "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
        "cust_category": cat_id,
        "cust_sub_category": sub_cat_id,
        "tags": "Google Maps: -6.2088,106.8456",
        "pkp": True,
    }
    customer_id = call_kw("sales.customer", "create", [customer_vals])
    print(f"  Created customer id={customer_id}")

    # Verify customer was created with correct fields
    customer = search_read("sales.customer", [["id", "=", customer_id]],
                           ["customer_name", "email", "pkp", "tags", "cust_category", "cust_sub_category"])
    assert len(customer) == 1, f"Customer not found after creation"
    c = customer[0]
    assert c["pkp"] == True, f"PKP should be True, got {c['pkp']}"
    assert c["tags"] == "Google Maps: -6.2088,106.8456", f"Tags mismatch: {c['tags']}"
    print(f"  [PASS] Customer created with pkp=True, tags set correctly")

    # ============================================================
    # TEST 6: Create Sold To address
    # ============================================================
    print("\n--- TEST 6: Create Sold To address ---")
    sold_to_id = call_kw("sales.sold_to", "create", [{
        "sold_name": "Main Office",
        "customer_id": customer_id,
        "address": "Jl. Sudirman No. 1",
    }])
    print(f"  Created sold_to id={sold_to_id}")

    sold_to = search_read("sales.sold_to", [["id", "=", sold_to_id]], ["sold_name", "address"])
    assert len(sold_to) == 1, "Sold To not found"
    assert sold_to[0]["sold_name"] == "Main Office"
    print(f"  [PASS] Sold To address created successfully")

    # ============================================================
    # TEST 7: Create Ship To address
    # ============================================================
    print("\n--- TEST 7: Create Ship To address ---")
    ship_to_id = call_kw("sales.ship_to", "create", [{
        "ship_name": "Warehouse",
        "customer_id": customer_id,
        "address": "Jl. Gatot Subroto No. 10",
    }])
    print(f"  Created ship_to id={ship_to_id}")

    ship_to = search_read("sales.ship_to", [["id", "=", ship_to_id]], ["ship_name", "address"])
    assert len(ship_to) == 1, "Ship To not found"
    assert ship_to[0]["ship_name"] == "Warehouse"
    print(f"  [PASS] Ship To address created successfully")

    # ============================================================
    # TEST 8: Create Bill To address
    # ============================================================
    print("\n--- TEST 8: Create Bill To address ---")
    bill_to_id = call_kw("sales.bill_to", "create", [{
        "bill_name": "Finance Department",
        "customer_id": customer_id,
        "address": "Jl. Thamrin No. 5",
    }])
    print(f"  Created bill_to id={bill_to_id}")

    bill_to = search_read("sales.bill_to", [["id", "=", bill_to_id]], ["bill_name", "address"])
    assert len(bill_to) == 1, "Bill To not found"
    assert bill_to[0]["bill_name"] == "Finance Department"
    print(f"  [PASS] Bill To address created successfully")

    # ============================================================
    # TEST 9: Verify customer has all addresses linked
    # ============================================================
    print("\n--- TEST 9: Verify customer addresses ---")
    customer_full = search_read("sales.customer", [["id", "=", customer_id]],
                               ["sold_to_ids", "ship_to_ids", "bill_to_ids"])
    assert len(customer_full) == 1, "Customer not found"
    cf = customer_full[0]
    assert len(cf["sold_to_ids"]) >= 1, f"Expected sold_to_ids, got {cf['sold_to_ids']}"
    assert len(cf["ship_to_ids"]) >= 1, f"Expected ship_to_ids, got {cf['ship_to_ids']}"
    assert len(cf["bill_to_ids"]) >= 1, f"Expected bill_to_ids, got {cf['bill_to_ids']}"
    print(f"  [PASS] Customer has Sold To: {cf['sold_to_ids']}, Ship To: {cf['ship_to_ids']}, Bill To: {cf['bill_to_ids']}")

    # ============================================================
    # TEST 10: Update Customer (toggle PKP)
    # ============================================================
    print("\n--- TEST 10: Update Customer PKP ---")
    call_kw("sales.customer", "write", [[customer_id], {"pkp": False}])
    updated = search_read("sales.customer", [["id", "=", customer_id]], ["pkp"])
    assert updated[0]["pkp"] == False, f"PKP should be False after update, got {updated[0]['pkp']}"
    print(f"  [PASS] PKP toggled to False successfully")

    # ============================================================
    # TEST 11: Verify cust_sub_category hierarchy
    # ============================================================
    print("\n--- TEST 11: Verify cust_sub_category hierarchy ---")
    sub_cat = search_read("sales.cust_sub_category", [["id", "=", sub_cat_id]], ["category_ref"])
    assert sub_cat[0]["category_ref"][0] == cat_id, f"category_ref mismatch: expected {cat_id}, got {sub_cat[0]['category_ref']}"
    print(f"  [PASS] Sub category linked to correct category (id={cat_id})")

    # ============================================================
    # TEST 12: Delete Customer (cleanup)
    # ============================================================
    print("\n--- TEST 12: Delete Customer (cleanup) ---")
    call_kw("sales.customer", "unlink", [[customer_id]])
    remaining = search_read("sales.customer", [["id", "=", customer_id]])
    assert len(remaining) == 0, "Customer should be deleted"
    print(f"  [PASS] Customer deleted successfully")

    # Cleanup sub category and category (skip if still used by others)
    call_kw("sales.cust_sub_category", "unlink", [[sub_cat_id]])
    try:
        call_kw("sales.cust_category", "unlink", [[cat_id]])
    except Exception:
        pass  # Category is still used by other customers
    print(f"  [PASS] Cleanup completed")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_test()
