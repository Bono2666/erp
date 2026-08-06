import pytest
import requests
import time as _time

from .config import BASE_URL, DB_NAME, LOGIN, PASSWORD, TIMEOUT


@pytest.fixture(scope="session")
def browser_type_launch_args():
    return {"channel": "chrome"}


@pytest.fixture(scope="session")
def browser_context_args():
    return {"viewport": {"width": 1280, "height": 720}}


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


def _get_session_cookie():
    """Authenticate via JSON-RPC and return session_id."""
    session = requests.Session()
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"db": DB_NAME, "login": LOGIN, "password": PASSWORD, "context": {}},
        "id": int(_time.time()),
    }
    resp = session.post(f"{BASE_URL}/web/session/authenticate", json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    result = resp.json()
    assert "result" in result, "API authentication failed"
    cookie_jar = resp.cookies
    session_id = cookie_jar.get("session_id", "")
    if not session_id:
        for c in resp.headers.get("Set-Cookie", "").split(","):
            if "session_id=" in c:
                session_id = c.split("session_id=")[1].split(";")[0].strip()
                break
    return session_id


@pytest.fixture
def logged_in_page(page, base_url):
    """Login to Odoo via cookie injection and return an authenticated page."""
    session_id = _get_session_cookie()
    page.context.add_cookies([{
        "name": "session_id",
        "value": session_id,
        "domain": "localhost",
        "path": "/",
    }])
    page.goto(f"{base_url}/web", timeout=TIMEOUT, wait_until="commit")
    _time.sleep(5)
    yield page
    try:
        page.goto("about:blank", timeout=5000, wait_until="commit")
    except Exception:
        pass
