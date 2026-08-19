import time

import pytest

from .config import BASE_URL, TIMEOUT, unique_suffix
from .helpers import api_session, call_kw, cleanup_model


PREFIX = "E2E-PC"

PRICE_CONDITION_URL = "#menu_id=212&action=248"


@pytest.fixture(autouse=True)
def _cleanup():
    """Remove price conditions created during the test."""
    yield
    session = api_session()
    cleanup_model(session, "sales.price_condition", [("price_condition_id", "like", f"{PREFIX}%")])


def _goto_list(page):
    """Open the price condition list view, retrying the deep-link which can race the app boot."""
    last_err = None
    for _ in range(4):
        page.goto(f"{BASE_URL}/web{PRICE_CONDITION_URL}", timeout=TIMEOUT, wait_until="commit")
        try:
            page.locator('.o_kanban_view, .o_list_view').first.wait_for(state="attached", timeout=8000)
            return
        except Exception as err:
            last_err = err
            time.sleep(3)
    raise RuntimeError(f"Failed to open Price Condition list view: {last_err}")


def _click_new(page):
    btn = page.locator("button:has-text('New')")
    for i in range(btn.count()):
        if btn.nth(i).is_visible():
            btn.nth(i).click()
            page.locator('.o_form_view').first.wait_for(state="visible", timeout=10000)
            return
    raise RuntimeError("No visible New button found")


def test_price_condition_manual_id_required(logged_in_page):
    """Price Condition ID is a required manual field: saving without it must fail validation."""
    page = logged_in_page
    _goto_list(page)
    _click_new(page)

    page.locator('div[name="price_name"] textarea, div[name="price_name"] input').first.fill("E2E No ID Price Condition")
    page.wait_for_timeout(300)

    page.get_by_role("button", name="Save").first.click()
    page.wait_for_timeout(2000)

    assert page.locator('.o_form_view').count() >= 1, "Form should remain open on validation error"
    assert page.locator('div[name="price_condition_id"].o_field_invalid').count() >= 1 or \
        page.locator('.o_field_invalid').count() >= 1, "Expected a required-field validation error"


def test_price_condition_manual_id_creation(logged_in_page):
    """Create a price condition entering the Price Condition ID manually; verify it is saved as-is."""
    page = logged_in_page
    suffix = unique_suffix()
    pc_id = f"{PREFIX}-{suffix}"

    _goto_list(page)
    _click_new(page)

    page.locator('div[name="price_condition_id"] input').first.fill(pc_id)
    page.locator('div[name="price_name"] textarea, div[name="price_name"] input').first.fill(f"E2E Manual ID Price Condition {suffix}")
    page.wait_for_timeout(300)

    page.get_by_role("button", name="Save").first.click()
    page.wait_for_timeout(3000)

    session = api_session()
    ids = call_kw(session, "sales.price_condition", "search", args=[[("price_condition_id", "=", pc_id)]])
    assert ids, f"Price Condition with ID {pc_id} was not saved"