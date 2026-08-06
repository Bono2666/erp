import requests
import time

from .config import BASE_URL, DB_NAME, LOGIN, PASSWORD, TIMEOUT


def api_session():
    """Return an authenticated requests.Session for jsonrpc calls."""
    session = requests.Session()
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"db": DB_NAME, "login": LOGIN, "password": PASSWORD, "context": {}},
        "id": int(time.time()),
    }
    resp = session.post(f"{BASE_URL}/web/session/authenticate", json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    assert "result" in resp.json(), "API authentication failed"
    return session


def call_kw(session, model, method, args=None, kwargs=None):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": method,
            "args": args or [],
            "kwargs": kwargs or {},
            "context": {},
        },
        "id": int(time.time()),
    }
    resp = session.post(f"{BASE_URL}/web/dataset/call_kw", json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    result = resp.json()
    if "error" in result:
        raise Exception(f"call_kw error {model}.{method}: {result['error']}")
    return result.get("result")


def cleanup_model(session, model, domain):
    """Search and unlink all matching records (silent failure if none)."""
    try:
        ids = call_kw(session, model, "search", args=[domain])
        if ids:
            call_kw(session, model, "unlink", args=[ids])
    except Exception:
        pass
