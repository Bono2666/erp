import requests

BASE_URL = "http://localhost:8018"
TIMEOUT = 30

def test_home_dashboard_visibility_and_navigation():
    session = requests.Session()
    headers = {"Content-Type": "application/json"}
    
    # Step 1: Authenticate user session with valid credentials
    auth_url = f"{BASE_URL}/web/session/authenticate"
    auth_payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": "odoo",
            "login": "admin",
            "password": "admin",
            "context": {}
        }
    }
    try:
        auth_response = session.post(auth_url, json=auth_payload, headers=headers, timeout=TIMEOUT)
        auth_response.raise_for_status()
        auth_result = auth_response.json()
        assert 'result' in auth_result and auth_result['result'].get('uid'), "Authentication failed or uid missing"
    except requests.RequestException as e:
        raise AssertionError(f"Authentication request failed: {e}")
    except (ValueError, KeyError) as e:
        raise AssertionError(f"Authentication response invalid: {e}")
    
    # Step 2: Call /web/dataset/call_kw/general.home to read dashboard visibility
    dashboard_url = f"{BASE_URL}/web/dataset/call_kw/general.home"
    dashboard_payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "general.home",
            "method": "read",
            "args": [],
            "kwargs": {}
        }
    }
    try:
        dashboard_response = session.post(dashboard_url, json=dashboard_payload, headers=headers, timeout=TIMEOUT)
        dashboard_response.raise_for_status()
        dashboard_data = dashboard_response.json()
        assert 'result' in dashboard_data, "Dashboard response missing result"
        modules = dashboard_data['result']
        # Validate that the response includes module cards (list expected)
        assert isinstance(modules, list), "Dashboard modules data is not a list"
        # Check that at least one module card is visible
        assert len(modules) > 0, "No visible module cards found on dashboard"
    except requests.RequestException as e:
        raise AssertionError(f"Dashboard visibility request failed: {e}")
    except (ValueError, KeyError, AssertionError) as e:
        raise AssertionError(f"Dashboard visibility response invalid or empty: {e}")
    
    # Additional: Attempt navigation simulation by checking presence of navigation shortcuts keys or URLs
    # Since this is backend test, just verify keys typically used for navigation shortcuts if present
    navigation_keys = ['menu_ids', 'shortcut_ids', 'module_cards', 'accessible_menus']
    has_navigation = any(any(key in module for key in navigation_keys) for module in modules if isinstance(module, dict))
    assert has_navigation, "No navigation shortcuts or accessible menu data found in dashboard response"

test_home_dashboard_visibility_and_navigation()
