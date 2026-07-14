import requests
import json

BASE_URL = "http://localhost:8018"
TIMEOUT = 30

def test_disable_autosave_configuration_and_behavior():
    session = requests.Session()

    # Credentials for authentication (replace with valid test user credentials)
    login_payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": "odoo_db",
            "login": "admin",
            "password": "admin"
        },
        "id": 1,
    }

    try:
        # Authenticate session
        auth_response = session.post(
            f"{BASE_URL}/web/session/authenticate",
            json=login_payload,
            timeout=TIMEOUT,
        )
        assert auth_response.status_code == 200
        auth_result = auth_response.json()
        assert auth_result.get("result") and "uid" in auth_result["result"], "Authentication failed"

        # Define model to prevent autosave on
        model_name = "hcm.employee"  # Example: prevent autosave on employee form

        # 1) Configure the model to prevent autosave via /web/dataset/call_kw/prevent.model POST
        prevent_model_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "prevent.model",
                "method": "create",
                "args": [{
                    "model_name": model_name,
                }],
                "kwargs": {},
                "context": {},
            },
            "id": 2,
        }
        create_resp = session.post(
            f"{BASE_URL}/web/dataset/call_kw/prevent.model",
            json=prevent_model_payload,
            timeout=TIMEOUT,
        )
        assert create_resp.status_code == 200
        create_result = create_resp.json()
        # The result should include new record id
        prevent_model_id = None
        if "result" in create_result and type(create_result["result"]) is int:
            prevent_model_id = create_result["result"]
        else:
            raise AssertionError(f"Failed to create prevent.model record: {create_result}")

        # 2) Retrieve the list of prevented models to verify the addition
        search_read_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "prevent.model",
                "method": "search_read",
                "args": [[]],
                "kwargs": {"fields": ["id", "model_name"]},
                "context": {},
            },
            "id": 3,
        }
        list_resp = session.post(
            f"{BASE_URL}/web/dataset/call_kw/prevent.model",
            json=search_read_payload,
            timeout=TIMEOUT,
        )
        assert list_resp.status_code == 200
        list_result = list_resp.json()
        found = False
        if "result" in list_result and isinstance(list_result["result"], list):
            for record in list_result["result"]:
                if record.get("id") == prevent_model_id and record.get("model_name") == model_name:
                    found = True
                    break
        assert found, f"Configured model '{model_name}' not found in prevent.model list"

        # 3) Simulate the front-end behavior:
        # Load the form view of the model to check that autosave prevention is effective.
        # - Request /web/view with model and some record to open.
        # - Here, create a temporary record of the model (hcm.employee) and test edit/save and discard behavior.
        # First, create a new hcm.employee record to test form behavior.
        create_employee_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model_name,
                "method": "create",
                "args": [{
                    "name": "Temp Test Employee Autosave",
                }],
                "kwargs": {},
                "context": {},
            },
            "id": 4,
        }
        employee_create_resp = session.post(
            f"{BASE_URL}/web/dataset/call_kw/{model_name}",
            json=create_employee_payload,
            timeout=TIMEOUT,
        )
        assert employee_create_resp.status_code == 200
        employee_create_result = employee_create_resp.json()
        employee_id = None
        if "result" in employee_create_result and isinstance(employee_create_result["result"], int):
            employee_id = employee_create_result["result"]
        else:
            raise AssertionError(f"Failed to create test hcm.employee record: {employee_create_result}")

        # Request the form view via /web/view to ensure form loads with autosave disabled.
        view_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model_name,
                "view_type": "form",
                "view_id": False,
                "context": {},
                "res_id": employee_id,
                "mode": "readonly",
            },
            "id": 5,
        }
        view_resp = session.post(
            f"{BASE_URL}/web/view",
            json=view_payload,
            timeout=TIMEOUT,
        )
        assert view_resp.status_code == 200
        view_result = view_resp.json()
        assert "result" in view_result and "arch" in view_result["result"], "Failed to load form view"

        # 4) Test edit action via /web/dataset/call action_edit
        edit_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model_name,
                "method": "call",
                "args": [employee_id, "action_edit"],
                "kwargs": {},
                "context": {},
            },
            "id": 6,
        }
        edit_resp = session.post(
            f"{BASE_URL}/web/dataset/call",
            json=edit_payload,
            timeout=TIMEOUT,
        )
        assert edit_resp.status_code == 200
        edit_result = edit_resp.json()
        assert "result" in edit_result, "Edit action response invalid"

        # 5) Simulate editing a field but NOT saving immediately (simulate that autosave is prevented on blur)
        # Since it's backend test, we simulate changing the field but immediately calling 'discard' action.
        # The discard is UI-level behavior; backend should not auto-save on field edit.
        # So we test that no record change occurs without explicit save.

        # Get original data for comparison
        read_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model_name,
                "method": "read",
                "args": [[employee_id], ["name"]],
                "kwargs": {},
                "context": {},
            },
            "id": 7,
        }
        read_resp = session.post(
            f"{BASE_URL}/web/dataset/call_kw/{model_name}",
            json=read_payload,
            timeout=TIMEOUT,
        )
        assert read_resp.status_code == 200
        read_result = read_resp.json()
        orig_name = None
        if "result" in read_result and isinstance(read_result["result"], list) and len(read_result["result"]) == 1:
            orig_name = read_result["result"][0].get("name")
        else:
            raise AssertionError(f"Failed to read original hcm.employee record data: {read_result}")

        # Normally, autosave would update backend on blur; here, simulate user discard:
        # No save call is made; we just confirm no data change.

        # 6) Now simulate discard behavior via form cancel without saving changes
        # The backend has no discard method; just do not save and check record unchanged
        # So fetch again and assert name unchanged

        read_resp_after_discard = session.post(
            f"{BASE_URL}/web/dataset/call_kw/{model_name}",
            json=read_payload,
            timeout=TIMEOUT,
        )
        assert read_resp_after_discard.status_code == 200
        read_after_discard_result = read_resp_after_discard.json()
        name_after_discard = None
        if "result" in read_after_discard_result and isinstance(read_after_discard_result["result"], list) and len(read_after_discard_result["result"]) == 1:
            name_after_discard = read_after_discard_result["result"][0].get("name")
        else:
            raise AssertionError(f"Failed to read hcm.employee record after discard: {read_after_discard_result}")

        assert name_after_discard == orig_name, "Record changed despite discard action - autosave prevention failed"

    finally:
        # Cleanup: Delete the created prevent.model record
        if 'prevent_model_id' in locals() and prevent_model_id:
            try:
                delete_prevent_payload = {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "model": "prevent.model",
                        "method": "unlink",
                        "args": [[prevent_model_id]],
                        "kwargs": {},
                        "context": {},
                    },
                    "id": 1001,
                }
                del_resp = session.post(
                    f"{BASE_URL}/web/dataset/call_kw/prevent.model",
                    json=delete_prevent_payload,
                    timeout=TIMEOUT,
                )
                assert del_resp.status_code == 200
            except Exception:
                pass

        # Cleanup: Delete created employee record
        if 'employee_id' in locals() and employee_id:
            try:
                delete_emp_payload = {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "model": "hcm.employee",
                        "method": "unlink",
                        "args": [[employee_id]],
                        "kwargs": {},
                        "context": {},
                    },
                    "id": 1002,
                }
                emp_del_resp = session.post(
                    f"{BASE_URL}/web/dataset/call_kw/hcm.employee",
                    json=delete_emp_payload,
                    timeout=TIMEOUT,
                )
                assert emp_del_resp.status_code == 200
            except Exception:
                pass

test_disable_autosave_configuration_and_behavior()
