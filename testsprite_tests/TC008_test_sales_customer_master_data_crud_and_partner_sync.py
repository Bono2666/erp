import requests
import uuid

BASE_URL = "http://localhost:8018"
TIMEOUT = 30


def test_sales_customer_master_data_crud_and_partner_sync():
    session = requests.Session()
    headers = {"Content-Type": "application/json"}
    username = "admin"
    password = "admin"
    # Authenticate
    auth_payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": "odoo",
            "login": username,
            "password": password,
            "context": {}
        },
        "id": int(uuid.uuid4().int % 100000)
    }

    auth_resp = session.post(
        f"{BASE_URL}/web/session/authenticate", json=auth_payload, headers=headers, timeout=TIMEOUT
    )
    assert auth_resp.status_code == 200, f"Authentication failed: {auth_resp.text}"
    auth_result = auth_resp.json()
    result_data = auth_result.get("result")
    assert result_data and "uid" in result_data, f"Authentication failed or uid missing in response, got: {auth_result}"
    # session cookie should be auto-handled by session

    def call_kw(model, method, args=None, kwargs=None):
        args = args or []
        kwargs = kwargs or {}
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args,
                "kwargs": kwargs,
            },
            "id": int(uuid.uuid4().int % 100000),
        }
        resp = session.post(f"{BASE_URL}/web/dataset/call_kw", json=payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        result = resp.json()
        if "error" in result:
            raise Exception(f"Error calling {model}.{method}: {result['error']}")
        return result.get("result")

    def search_read(model, domain=None, fields=None):
        domain = domain or []
        fields = fields or []
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": "search_read",
                "args": [domain],
                "kwargs": {"fields": fields},
            },
            "id": int(uuid.uuid4().int % 100000),
        }
        resp = session.post(f"{BASE_URL}/web/dataset/search_read", json=payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        result = resp.json()
        if "error" in result:
            raise Exception(f"Error search_read {model}: {result['error']}")
        return result.get("result", [])

    # Step 1: Create customer category
    cust_category_vals = {
        "name": f"Category_{uuid.uuid4().hex[:8]}"
    }
    cust_category_id = None
    cust_type_id = None
    cust_area_id = None
    customer_id = None
    ship_to_id = None

    try:
        cust_category_create_result = call_kw(
            "sales.cust_category", "create", args=[cust_category_vals]
        )
        cust_category_id = cust_category_create_result
        assert isinstance(cust_category_id, int) and cust_category_id > 0, "Invalid category ID"

        # Step 2: Create customer type
        cust_type_vals = {
            "name": f"Type_{uuid.uuid4().hex[:8]}"
        }
        cust_type_id = call_kw("sales.cust_type", "create", args=[cust_type_vals])
        assert isinstance(cust_type_id, int) and cust_type_id > 0, "Invalid customer type ID"

        # Step 3: Create customer area
        cust_area_vals = {
            "name": f"Area_{uuid.uuid4().hex[:8]}"
        }
        cust_area_id = call_kw("sales.cust_area", "create", args=[cust_area_vals])
        assert isinstance(cust_area_id, int) and cust_area_id > 0, "Invalid customer area ID"

        # Step 4: Create customer with automatic partner creation and address hierarchy support
        # To support address hierarchy, normally would reference country, state, etc., but this test focuses on sales.* endpoints and automatic partner creation
        customer_vals = {
            "name": f"Customer_{uuid.uuid4().hex[:8]}",
            "cust_category_id": cust_category_id,
            "cust_type_id": cust_type_id,
            "cust_area_id": cust_area_id,
            "street": "123 Test Street",
            "street2": "Suite 100",
            "city": "Test City",
            "zip": "12345",
            # Assuming country/state/city/district are handled with ids, but since no direct creation/use here, they are omitted
            # The backend is expected to auto-create linked res.partner
        }
        customer_id = call_kw("sales.customer", "create", args=[customer_vals])
        assert isinstance(customer_id, int) and customer_id > 0, "Invalid customer ID"

        # Confirm auto-created partner exists via sales.customer read
        customer_data = call_kw("sales.customer", "read", args=[[customer_id]], kwargs={"fields": ["name", "res_partner_id"]})
        assert customer_data and isinstance(customer_data, list) and len(customer_data) == 1, "Failed to read created customer"
        partner_id = customer_data[0].get("res_partner_id")
        # Partner id is typically a tuple: (id, display_name)
        assert isinstance(partner_id, (list, tuple)) and len(partner_id) >= 1 and isinstance(partner_id[0], int), "Partner not linked or invalid"

        # Step 5: Create ship-to address linked to customer
        ship_to_vals = {
            "name": f"ShipTo_{uuid.uuid4().hex[:8]}",
            "customer_id": customer_id,
            "street": "456 Delivery Ave",
            "city": "Delivery City",
            "zip": "67890",
        }
        ship_to_id = call_kw("sales.ship_to", "create", args=[ship_to_vals])
        assert isinstance(ship_to_id, int) and ship_to_id > 0, "Invalid ship-to ID"

        # Step 6: Read back ship-to address and verify linkage
        ship_to_data = call_kw("sales.ship_to", "read", args=[[ship_to_id]], kwargs={"fields": ["name", "customer_id"]})
        assert ship_to_data and len(ship_to_data) == 1, "Failed to read ship-to address"
        linked_customer_id = ship_to_data[0].get("customer_id")
        # customer_id typically tuple (id, display_name)
        assert isinstance(linked_customer_id, (list, tuple)) and linked_customer_id[0] == customer_id, "Ship-to not linked to customer"

        # Step 7: Update customer (simulate edit/save form pattern)
        new_city = "Updated City"
        update_result = call_kw("sales.customer", "write", args=[[customer_id], {"city": new_city}])
        assert update_result is True, "Customer update failed"

        updated_customer = call_kw("sales.customer", "read", args=[[customer_id]], kwargs={"fields": ["city"]})
        assert updated_customer[0]["city"] == new_city, "Customer city update not persisted"

        # Step 8: Delete ship-to address and verify deletion
        delete_ship_to_result = call_kw("sales.ship_to", "unlink", args=[[ship_to_id]])
        assert delete_ship_to_result is True, "Failed to delete ship-to address"

        # Confirm deletion by search_read
        ship_to_check = search_read("sales.ship_to", domain=[("id", "=", ship_to_id)], fields=["id"])
        assert not ship_to_check, "Deleted ship-to address still present"

        ship_to_id = None  # Mark as deleted

        # Step 9: Delete customer and verify deletion (expect success if no active sales order)
        delete_customer_result = call_kw("sales.customer", "unlink", args=[[customer_id]])
        assert delete_customer_result is True, "Failed to delete customer"

        # Confirm deletion by search_read
        customer_check = search_read("sales.customer", domain=[("id", "=", customer_id)], fields=["id"])
        assert not customer_check, "Deleted customer still present"

        customer_id = None  # Mark as deleted

        # Step 10: Delete customer category, type, area
        if cust_category_id:
            delete_cat = call_kw("sales.cust_category", "unlink", args=[[cust_category_id]])
            assert delete_cat is True, "Failed to delete customer category"
            cust_category_id = None
        if cust_type_id:
            delete_type = call_kw("sales.cust_type", "unlink", args=[[cust_type_id]])
            assert delete_type is True, "Failed to delete customer type"
            cust_type_id = None
        if cust_area_id:
            delete_area = call_kw("sales.cust_area", "unlink", args=[[cust_area_id]])
            assert delete_area is True, "Failed to delete customer area"
            cust_area_id = None

    finally:
        # Cleanup resources that might still exist after failure
        try:
            if ship_to_id:
                call_kw("sales.ship_to", "unlink", args=[[ship_to_id]])
        except Exception:
            pass
        try:
            if customer_id:
                call_kw("sales.customer", "unlink", args=[[customer_id]])
        except Exception:
            pass
        try:
            if cust_category_id:
                call_kw("sales.cust_category", "unlink", args=[[cust_category_id]])
        except Exception:
            pass
        try:
            if cust_type_id:
                call_kw("sales.cust_type", "unlink", args=[[cust_type_id]])
        except Exception:
            pass
        try:
            if cust_area_id:
                call_kw("sales.cust_area", "unlink", args=[[cust_area_id]])
        except Exception:
            pass

test_sales_customer_master_data_crud_and_partner_sync()
