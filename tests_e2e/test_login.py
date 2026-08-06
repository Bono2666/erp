from .config import BASE_URL, TIMEOUT
from .conftest import _get_session_cookie


def test_login_success(page):
    """Verify successful login lands on /web with navbar visible."""
    session_id = _get_session_cookie()
    page.context.add_cookies([{
        "name": "session_id",
        "value": session_id,
        "domain": "localhost",
        "path": "/",
    }])
    page.goto(f"{BASE_URL}/web", timeout=TIMEOUT, wait_until="commit")
    page.wait_for_timeout(3000)
    assert "/web" in page.url
    assert page.locator(".o_main_navbar, .o_navbar, .o_menu_sections").count() >= 1


def test_login_wrong_password(page):
    """Verify wrong password shows error."""
    import requests, time
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"db": "erp", "login": "trihambono@gmail.com", "password": "wrong_password", "context": {}},
        "id": int(time.time()),
    }
    resp = requests.post(f"{BASE_URL}/web/session/authenticate", json=payload, timeout=TIMEOUT)
    result = resp.json()
    assert "error" in result or result.get("result", {}).get("uid") is False


def test_logout(logged_in_page):
    """Verify session cookie removal."""
    logged_in_page.context.clear_cookies()
    logged_in_page.goto(f"{BASE_URL}/web/login", timeout=TIMEOUT, wait_until="commit")
    logged_in_page.wait_for_timeout(1000)
    assert "/web/login" in logged_in_page.url
