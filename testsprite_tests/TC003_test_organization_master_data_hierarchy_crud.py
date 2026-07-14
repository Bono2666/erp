import requests
import json

BASE_URL = "http://localhost:8018"
TIMEOUT = 30

USERNAME = "admin"    # Replace with valid username
PASSWORD = "admin"    # Replace with valid password
DB = "demo"           # Replace with the correct database name

HEADERS = {
    "Content-Type": "application/json"
}

def authenticate():
    url = f"{BASE_URL}/web/session/authenticate"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": DB,
            "login": USERNAME,
            "password": PASSWORD
        }
    }
    resp = requests.post(url, headers=HEADERS, json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    result = resp.json()
    session_info = result.get("result", {})
    session_id = session_info.get("session_id")
    uid = session_info.get("uid")
    assert session_id is not None, "Authentication failed: no session_id"
    assert uid is not None, "Authentication failed: no uid"
    cookies = resp.cookies
    return cookies, uid

def call_kw(model, method, args=None, kwargs=None, cookies=None):
    url = f"{BASE_URL}/web/dataset/call_kw/{model}"
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": method,
            "args": args,
            "kwargs": kwargs,
            "context": {},
        }
    }
    resp = requests.post(url, headers=HEADERS, json=payload, cookies=cookies, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()

def search_read(model, domain=None, fields=None, cookies=None):
    url = f"{BASE_URL}/web/dataset/search_read"
    if domain is None:
        domain = []
    if fields is None:
        fields = []
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "domain": domain,
            "fields": fields,
            "limit": 100,
            "context": {},
        }
    }
    resp = requests.post(url, headers=HEADERS, json=payload, cookies=cookies, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()

def test_organization_master_data_hierarchy_crud():
    cookies, uid = authenticate()

    division_id = department_id = position_id = company_id = location_id = level_grade_id = None

    try:
        # 1. Create Division
        division_name = "Test Division"
        res = call_kw(
            "general.division",
            "create",
            args=[{"name": division_name}],
            cookies=cookies
        )
        division_id = res.get("result")
        assert isinstance(division_id, int) and division_id > 0, "Failed to create Division"

        # 2. Read Division to verify
        division_read = search_read("general.division", domain=[("id", "=", division_id)], fields=["id", "name"], cookies=cookies)
        records = division_read.get("result", {}).get("records", [])
        assert len(records) == 1 and records[0]["name"] == division_name, "Division not found or name mismatch"

        # 3. Create Department under Division
        department_name = "Test Department"
        res = call_kw(
            "general.department",
            "create",
            args=[{"name": department_name, "division_id": division_id}],
            cookies=cookies
        )
        department_id = res.get("result")
        assert isinstance(department_id, int) and department_id > 0, "Failed to create Department"

        # 4. Read Department and check linked division
        department_read = search_read("general.department", domain=[("id", "=", department_id)], fields=["id", "name", "division_id"], cookies=cookies)
        records = department_read.get("result", {}).get("records", [])
        assert len(records) == 1, "Department not found"
        dep = records[0]
        assert dep["name"] == department_name, "Department name mismatch"
        assert dep["division_id"][0] == division_id, "Department not linked to correct Division"

        # 5. Create Position under Department
        position_name = "Test Position"
        res = call_kw(
            "general.position",
            "create",
            args=[{"name": position_name, "department_id": department_id}],
            cookies=cookies
        )
        position_id = res.get("result")
        assert isinstance(position_id, int) and position_id > 0, "Failed to create Position"

        # 6. Read Position and check linked department
        position_read = search_read("general.position", domain=[("id", "=", position_id)], fields=["id", "name", "department_id"], cookies=cookies)
        records = position_read.get("result", {}).get("records", [])
        assert len(records) == 1, "Position not found"
        pos = records[0]
        assert pos["name"] == position_name, "Position name mismatch"
        assert pos["department_id"][0] == department_id, "Position not linked to correct Department"

        # 7. Create Company
        company_name = "Test Company"
        res = call_kw(
            "general.company",
            "create",
            args=[{"name": company_name}],
            cookies=cookies
        )
        company_id = res.get("result")
        assert isinstance(company_id, int) and company_id > 0, "Failed to create Company"

        # 8. Read Company to verify
        company_read = search_read("general.company", domain=[("id", "=", company_id)], fields=["id", "name"], cookies=cookies)
        records = company_read.get("result", {}).get("records", [])
        assert len(records) == 1 and records[0]["name"] == company_name, "Company not found or name mismatch"

        # 9. Create Location
        location_name = "Test Location"
        res = call_kw(
            "general.location",
            "create",
            args=[{"name": location_name}],
            cookies=cookies
        )
        location_id = res.get("result")
        assert isinstance(location_id, int) and location_id > 0, "Failed to create Location"

        # 10. Read Location to verify
        location_read = search_read("general.location", domain=[("id", "=", location_id)], fields=["id", "name"], cookies=cookies)
        records = location_read.get("result", {}).get("records", [])
        assert len(records) == 1 and records[0]["name"] == location_name, "Location not found or name mismatch"

        # 11. Create Level/Grade
        level_grade_name = "Test Level/Grade"
        res = call_kw(
            "general.level_grade",
            "create",
            args=[{"name": level_grade_name}],
            cookies=cookies
        )
        level_grade_id = res.get("result")
        assert isinstance(level_grade_id, int) and level_grade_id > 0, "Failed to create Level/Grade"

        # 12. Read Level/Grade to verify
        level_grade_read = search_read("general.level_grade", domain=[("id", "=", level_grade_id)], fields=["id", "name"], cookies=cookies)
        records = level_grade_read.get("result", {}).get("records", [])
        assert len(records) == 1 and records[0]["name"] == level_grade_name, "Level/Grade not found or name mismatch"

        # 13. Update Department to link to a different Division (test update)
        new_division_name = "Test Division Updated"
        res_upd_div = call_kw(
            "general.division",
            "write",
            args=[[division_id], {"name": new_division_name}],
            cookies=cookies
        )
        assert res_upd_div.get("result") is True, "Failed to update Division name"

        # Confirm update
        division_read_updated = search_read("general.division", domain=[("id", "=", division_id)], fields=["name"], cookies=cookies)
        records = division_read_updated.get("result", {}).get("records", [])
        assert records[0]["name"] == new_division_name, "Division name not updated"

        # 14. Delete Position
        res_del_position = call_kw(
            "general.position",
            "unlink",
            args=[[position_id]],
            cookies=cookies
        )
        assert res_del_position.get("result") is True, "Failed to delete Position"

        # Confirm Position deletion
        position_read_deleted = search_read("general.position", domain=[("id", "=", position_id)], fields=["id"], cookies=cookies)
        assert len(position_read_deleted.get("result", {}).get("records", [])) == 0, "Position not deleted"

        position_id = None  # reset since deleted

    finally:
        # Cleanup all created records in reverse order (if still exist)

        def safe_delete(model, record_id):
            if record_id is not None:
                try:
                    res = call_kw(model, "unlink", args=[[record_id]], cookies=cookies)
                    if res.get("result") is not True:
                        print(f"Warning: Could not delete {model} id={record_id}")
                except Exception as e:
                    print(f"Warning: Exception deleting {model} id={record_id}: {str(e)}")

        safe_delete("general.position", position_id)
        safe_delete("general.department", department_id)
        safe_delete("general.division", division_id)
        safe_delete("general.company", company_id)
        safe_delete("general.location", location_id)
        safe_delete("general.level_grade", level_grade_id)

test_organization_master_data_hierarchy_crud()