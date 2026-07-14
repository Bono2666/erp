import requests

BASE_URL = "http://localhost:8018"
TIMEOUT = 30

# Replace with valid Odoo credentials for the test environment
USERNAME = "admin"
PASSWORD = "admin"

HEADERS = {
    "Content-Type": "application/json",
}

def authenticate():
    url = f"{BASE_URL}/web/session/authenticate"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": "odoo",
            "login": USERNAME,
            "password": PASSWORD,
        }
    }
    resp = requests.post(url, json=payload, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    result = resp.json()
    assert 'result' in result and result['result'] and 'uid' in result['result'], "Authentication failed"
    cookies = resp.cookies
    return cookies

def call_kw(model, method, params, cookies):
    url = f"{BASE_URL}/web/dataset/call_kw/{model}"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": method,
            "args": [],
            "kwargs": params,
        }
    }
    resp = requests.post(url, json=payload, headers=HEADERS, cookies=cookies, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()

def search_read(model, domain, fields, cookies):
    url = f"{BASE_URL}/web/dataset/search_read"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "domain": domain,
            "fields": fields,
            "limit": 1,
        }
    }
    resp = requests.post(url, json=payload, headers=HEADERS, cookies=cookies, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()

def test_address_hierarchy_master_data_crud_and_onchange():
    cookies = authenticate()
    created_ids = {
        "country_id": None,
        "state_id": None,
        "city_id": None,
        "district_id": None,
        "village_id": None,
    }
    try:
        # Create Country
        country_vals = {
            "name": "Testland",
            "code": "TL",
        }
        resp = call_kw(
            "general.country",
            "create",
            {"vals": country_vals},
            cookies
        )
        assert 'result' in resp and isinstance(resp['result'], int), "Country creation failed"
        created_ids["country_id"] = resp['result']

        # Create State linked to Country
        state_vals = {
            "name": "Teststate",
            "country_id": created_ids["country_id"],
            "code": "TS",
        }
        resp = call_kw(
            "general.state",
            "create",
            {"vals": state_vals},
            cookies
        )
        assert 'result' in resp and isinstance(resp['result'], int), "State creation failed"
        created_ids["state_id"] = resp['result']

        # Create City linked to State
        city_vals = {
            "name": "Testcity",
            "state_id": created_ids["state_id"],
        }
        resp = call_kw(
            "general.city",
            "create",
            {"vals": city_vals},
            cookies
        )
        assert 'result' in resp and isinstance(resp['result'], int), "City creation failed"
        created_ids["city_id"] = resp['result']

        # Create District linked to City
        district_vals = {
            "name": "Testdistrict",
            "city_id": created_ids["city_id"],
        }
        resp = call_kw(
            "general.district",
            "create",
            {"vals": district_vals},
            cookies
        )
        assert 'result' in resp and isinstance(resp['result'], int), "District creation failed"
        created_ids["district_id"] = resp['result']

        # Perform onchange on Village to auto-fill fields based on district selection
        village_onchange_params = {
            "vals": {"district_id": created_ids["district_id"]},
            "state": {},  # No state info passed, typical for onchange
            "field_name": "district_id",
        }
        resp = call_kw(
            "general.village",
            "onchange_district_id",
            village_onchange_params,
            cookies
        )
        assert 'result' in resp and isinstance(resp['result'], dict), "Village onchange failed"
        onchange_data = resp['result'].get('value', {})
        # The onchange should autofill district, city, state, country references in the village form
        assert onchange_data.get("district_id") == created_ids["district_id"], "Village onchange missing district_id"
        # Since district->city->state->country are linked, check keys are present and consistent
        # We don't have exact IDs for city/state/country in onchange - it's UI-specific - but presence means success
        for key in ["city_id", "state_id", "country_id"]:
            assert key in onchange_data, f"Village onchange missing {key}"

        # Save Village with district linked and onchange auto-fill data merged
        village_vals = {
            "name": "Testvillage",
            "district_id": created_ids["district_id"],
            "city_id": onchange_data.get("city_id", False),
            "state_id": onchange_data.get("state_id", False),
            "country_id": onchange_data.get("country_id", False),
        }
        resp = call_kw(
            "general.village",
            "create",
            {"vals": village_vals},
            cookies
        )
        assert 'result' in resp and isinstance(resp['result'], int), "Village creation failed"
        created_ids["village_id"] = resp['result']

        # Verify that all records link properly by reading village and checking fields cascade
        read_resp = search_read(
            "general.village",
            [("id", "=", created_ids["village_id"])],
            ["district_id", "city_id", "state_id", "country_id", "name"],
            cookies
        )
        assert 'result' in read_resp and 'records' in read_resp['result'], "Village search_read failed"
        records = read_resp['result']['records']
        assert len(records) == 1, "Village record not found"
        village = records[0]
        assert village["id"] == created_ids["village_id"], "Village ID mismatch"
        assert village["district_id"] and village["district_id"][0] == created_ids["district_id"], "District linkage invalid"
        assert village["city_id"] and village["city_id"][0] == created_ids["city_id"], "City linkage invalid"
        assert village["state_id"] and village["state_id"][0] == created_ids["state_id"], "State linkage invalid"
        assert village["country_id"] and village["country_id"][0] == created_ids["country_id"], "Country linkage invalid"
    finally:
        # Cleanup in reverse order to respect FK constraints - best effort ignoring errors
        if created_ids.get("village_id"):
            try:
                call_kw("general.village", "unlink", {"ids": [created_ids["village_id"]]}, cookies)
            except Exception:
                pass
        if created_ids.get("district_id"):
            try:
                call_kw("general.district", "unlink", {"ids": [created_ids["district_id"]]}, cookies)
            except Exception:
                pass
        if created_ids.get("city_id"):
            try:
                call_kw("general.city", "unlink", {"ids": [created_ids["city_id"]]}, cookies)
            except Exception:
                pass
        if created_ids.get("state_id"):
            try:
                call_kw("general.state", "unlink", {"ids": [created_ids["state_id"]]}, cookies)
            except Exception:
                pass
        if created_ids.get("country_id"):
            try:
                call_kw("general.country", "unlink", {"ids": [created_ids["country_id"]]}, cookies)
            except Exception:
                pass

test_address_hierarchy_master_data_crud_and_onchange()
