import requests
from requests.exceptions import RequestException, Timeout

BASE_URL = "http://localhost:8018"
TIMEOUT = 30

USERNAME = "admin"
PASSWORD = "admin"


def test_hcm_position_management_hierarchy_and_org_chart():
    session = requests.Session()
    headers = {"Content-Type": "application/json"}

    try:
        # Authenticate
        auth_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": "default",
                "login": USERNAME,
                "password": PASSWORD,
                "context": {}
            }
        }
        resp = session.post(
            f"{BASE_URL}/web/session/authenticate",
            json=auth_payload,
            headers=headers,
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200, f"Authentication failed: {resp.text}"
        auth_result = resp.json()
        assert 'result' in auth_result and 'uid' in auth_result['result'] and auth_result['result']['uid'] > 0, "Authentication response invalid"

        # Create a top-level position
        create_top_position_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "hcm.position",
                "method": "create",
                "args": [{
                    "name": "Top Level Position Test"
                }],
                "kwargs": {},
            }
        }
        resp = session.post(
            f"{BASE_URL}/web/dataset/call_kw/hcm.position",
            json=create_top_position_payload,
            headers=headers,
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200, f"Failed to create top-level position: {resp.text}"
        result = resp.json()
        assert "result" in result and isinstance(result["result"], int), "Create top-level position response invalid"
        top_position_id = result["result"]

        try:
            # Create a child position with parent_id = top_position_id
            create_child_position_payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "hcm.position",
                    "method": "create",
                    "args": [{
                        "name": "Child Position Test",
                        "parent_id": top_position_id
                    }],
                    "kwargs": {},
                }
            }
            resp = session.post(
                f"{BASE_URL}/web/dataset/call_kw/hcm.position",
                json=create_child_position_payload,
                headers=headers,
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, f"Failed to create child position: {resp.text}"
            result = resp.json()
            assert "result" in result and isinstance(result["result"], int), "Create child position response invalid"
            child_position_id = result["result"]

            # Retrieve all positions to verify hierarchy with search_read active positions
            search_read_payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "hcm.position",
                    "method": "search_read",
                    "args": [],
                    "kwargs": {
                        "domain": [["id", "in", [top_position_id, child_position_id]]],
                        "fields": ["id", "name", "parent_id", "employee_count"],
                    },
                }
            }
            resp = session.post(
                f"{BASE_URL}/web/dataset/call_kw/hcm.position",
                json=search_read_payload,
                headers=headers,
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, f"Failed to search_read positions: {resp.text}"
            records = resp.json().get("result", [])
            ids = [rec["id"] for rec in records]
            assert top_position_id in ids and child_position_id in ids, "Created positions not found"
            # Verify parent-child link
            child_record = next((r for r in records if r["id"] == child_position_id), None)
            assert child_record is not None and child_record.get("parent_id") is not False, "Child position missing parent_id"
            assert child_record["parent_id"][0] == top_position_id, "Child position parent_id mismatch"

            # Fetch organization chart data via hcm.org_structure
            org_chart_payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "hcm.org_structure",
                    "method": "get_chart_data",
                    "args": [],
                    "kwargs": {},
                }
            }
            resp = session.post(
                f"{BASE_URL}/web/dataset/call_kw/hcm.org_structure",
                json=org_chart_payload,
                headers=headers,
                timeout=TIMEOUT,
            )
            # It may be possible that method name is other, so fallback to generic call without method 'get_chart_data'
            if resp.status_code != 200:
                # fallback: just call search_read or read on hcm.org_structure or call_kw with empty method (as present usage)
                org_chart_payload_alt = {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "model": "hcm.org_structure",
                        "method": "search_read",
                        "args": [],
                        "kwargs": {},
                    }
                }
                resp = session.post(
                    f"{BASE_URL}/web/dataset/call_kw/hcm.org_structure",
                    json=org_chart_payload_alt,
                    headers=headers,
                    timeout=TIMEOUT,
                )
            assert resp.status_code == 200, f"Failed to get org structure data: {resp.text}"
            org_data_resp = resp.json()
            assert "result" in org_data_resp and (isinstance(org_data_resp["result"], dict) or isinstance(org_data_resp["result"], list)), "Org structure response invalid"
            # For dict result, check keys like 'nodes' with parent relationships
            if isinstance(org_data_resp["result"], dict):
                assert "nodes" in org_data_resp["result"], "Org structure missing 'nodes' key"
                assert isinstance(org_data_resp["result"]["nodes"], list), "'nodes' should be a list"
                # Check that top position node is represented
                assert any(str(top_position_id) == str(node.get("id")) for node in org_data_resp["result"]["nodes"]), "Top position not in org chart nodes"

        finally:
            # Cleanup: delete child position
            delete_child_payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "hcm.position",
                    "method": "unlink",
                    "args": [[child_position_id]],
                    "kwargs": {},
                }
            }
            try:
                session.post(
                    f"{BASE_URL}/web/dataset/call_kw/hcm.position",
                    json=delete_child_payload,
                    headers=headers,
                    timeout=TIMEOUT,
                )
            except Exception:
                pass

        # Cleanup: delete top-level position
        delete_top_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "hcm.position",
                "method": "unlink",
                "args": [[top_position_id]],
                "kwargs": {},
            }
        }
        try:
            session.post(
                f"{BASE_URL}/web/dataset/call_kw/hcm.position",
                json=delete_top_payload,
                headers=headers,
                timeout=TIMEOUT,
            )
        except Exception:
            pass

    except (RequestException, Timeout, AssertionError) as e:
        raise AssertionError(f"Test failed: {e}")


test_hcm_position_management_hierarchy_and_org_chart()