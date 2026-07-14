import requests

BASE_URL = "http://localhost:8018"
TIMEOUT = 30


def test_rbac_user_and_access_management_crud_and_permissions():
    session = requests.Session()
    headers = {"Content-Type": "application/json"}

    # Authenticate as admin user
    auth_payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": "odoo",
            "login": "admin",
            "password": "admin",
            "context": {},
        }
    }
    auth_resp = session.post(f"{BASE_URL}/web/session/authenticate", json=auth_payload, headers=headers, timeout=TIMEOUT)
    assert auth_resp.status_code == 200, f"Authentication failed: {auth_resp.text}"
    auth_data = auth_resp.json()
    assert "result" in auth_data and auth_data["result"].get("uid"), "Authentication response missing user id"

    # Helper function to call /web/dataset/call_kw endpoint
    def call_kw(model, method, args=None, kwargs=None, context=None):
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        params = {
            "model": model,
            "method": method,
            "args": args,
            "kwargs": kwargs,
            "context": context or {},
        }
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
        }
        resp = session.post(f"{BASE_URL}/web/dataset/call_kw/{model}", json=payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    # 1. Create a custom user via general.custom_users (auto-creates linked res.users)
    custom_user_vals = {
        "name": "Test RBAC User",
        "login": "test_rbac_user",
        "password": "testpass123",
        "email": "test_rbac@example.com",
        "active": True,
    }
    try:
        create_resp = call_kw("general.custom_users", "create", args=[custom_user_vals])
        assert "result" in create_resp and isinstance(create_resp["result"], int), \
            f"Failed to create custom user: {create_resp}"

        custom_user_id = create_resp["result"]

        # 2. Assign menu CRUD rights via general.auth for this user
        # Example: grant create, read, write, unlink on menu id 1 (assuming menu id 1 exists)
        # The structure and field names of general.auth are assumed: user_id, menu_id, create, read, write, unlink
        auth_vals = {
            "user_id": custom_user_id,
            "menu_id": 1,
            "create": True,
            "read": True,
            "write": True,
            "unlink": False,
        }
        auth_create_resp = call_kw("general.auth", "create", args=[auth_vals])
        assert "result" in auth_create_resp and isinstance(auth_create_resp["result"], int), \
            f"Failed to create general.auth access rights: {auth_create_resp}"

        auth_id = auth_create_resp["result"]

        # 3. Update user profile preferences via general.preferences
        pref_vals = {
            "user_id": custom_user_id,
            "language": "en_US",
            "timezone": "Europe/Brussels",
            "theme": "light",
        }
        pref_create_resp = call_kw("general.preferences", "create", args=[pref_vals])
        assert "result" in pref_create_resp and isinstance(pref_create_resp["result"], int), \
            f"Failed to create user preferences: {pref_create_resp}"

        pref_id = pref_create_resp["result"]

        # 4. Change password for custom user via general.password (admin password change wizard)
        pwd_change_vals = {
            "user_id": custom_user_id,
            "new_password": "new_testpass456",
        }
        pwd_change_resp = call_kw("general.password", "change_password", args=[pwd_change_vals])
        # Changed method name to 'change_password' to match typical usage.
        assert "result" in pwd_change_resp, f"Password change response missing: {pwd_change_resp}"

        # 5. Authenticate as custom user with new password to validate password change
        auth_payload_custom = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": "odoo",
                "login": "test_rbac_user",
                "password": "new_testpass456",
                "context": {},
            }
        }
        auth_custom_resp = session.post(f"{BASE_URL}/web/session/authenticate", json=auth_payload_custom, headers=headers, timeout=TIMEOUT)
        assert auth_custom_resp.status_code == 200, f"Custom user login failed: {auth_custom_resp.text}"
        auth_custom_data = auth_custom_resp.json()
        assert "result" in auth_custom_data and auth_custom_data["result"].get("uid"), "Custom user login response missing user id"

        # 6. As custom user, try modifying permissions (expect authorization error)
        # We'll attempt to create a new auth record (unallowed)
        try:
            auth_mod_payload = {
                "model": "general.auth",
                "method": "create",
                "args": [{
                    "user_id": custom_user_id,
                    "menu_id": 2,
                    "create": True,
                    "read": True,
                    "write": False,
                    "unlink": False,
                }],
                "kwargs": {},
            }
            auth_mod_call = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": auth_mod_payload,
            }
            mod_resp = session.post(f"{BASE_URL}/web/dataset/call_kw/general.auth", json=auth_mod_call, headers=headers, timeout=TIMEOUT)
            # If status code 200, check if error in response json
            mod_resp_json = mod_resp.json()
            assert ("error" in mod_resp_json) or (mod_resp.status_code != 200 and mod_resp.status_code != 500), \
                "Expected authorization error when modifying permissions but succeeded."
        except requests.HTTPError as e:
            # Expected authorization error may cause HTTP error
            assert e.response.status_code in [403, 401], f"Unexpected HTTP error: {e}"

        # 7. As custom user, attempt creating another custom user (expect access denied)
        try:
            new_user_vals = {
                "name": "Should Fail User",
                "login": "fail_user",
                "password": "failpass",
                "email": "fail@example.com",
            }
            user_create_payload = {
                "model": "general.custom_users",
                "method": "create",
                "args": [new_user_vals],
                "kwargs": {},
            }
            user_create_call = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": user_create_payload,
            }
            create_resp_user = session.post(f"{BASE_URL}/web/dataset/call_kw/general.custom_users", json=user_create_call, headers=headers, timeout=TIMEOUT)
            create_resp_json = create_resp_user.json()
            # Should fail by returning error or HTTP error code
            assert ("error" in create_resp_json) or (create_resp_user.status_code != 200), \
                "Non-admin user should not be able to create custom users."
        except requests.HTTPError as e:
            assert e.response.status_code in [403, 401], f"Unexpected HTTP error: {e}"

    finally:
        # Cleanup: delete created records with admin session
        if 'pref_id' in locals():
            try:
                call_kw("general.preferences", "unlink", args=[[pref_id]])
            except Exception:
                pass
        if 'auth_id' in locals():
            try:
                call_kw("general.auth", "unlink", args=[[auth_id]])
            except Exception:
                pass
        if 'custom_user_id' in locals():
            try:
                call_kw("general.custom_users", "unlink", args=[[custom_user_id]])
            except Exception:
                pass


test_rbac_user_and_access_management_crud_and_permissions()
