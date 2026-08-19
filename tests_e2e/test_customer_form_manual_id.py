import time

import pytest

from .config import BASE_URL, TIMEOUT, unique_suffix
from .helpers import api_session, call_kw, cleanup_model


PREFIX = "E2E-CUST"

CUSTOMER_URL = "#menu_id=217&action=249"


@pytest.fixture(autouse=True)
def _cleanup():
    """Remove customers created during the test."""
    yield
    session = api_session()
    cleanup_model(session, "sales.customer", [("customer_id", "like", f"{PREFIX}%")])


def _goto_list(page):
    """Open the customer list view, retrying the deep-link which can race the app boot."""
    last_err = None
    for _ in range(4):
        page.goto(f"{BASE_URL}/web{CUSTOMER_URL}", timeout=TIMEOUT, wait_until="commit")
        try:
            page.locator('.o_kanban_view, .o_list_view').first.wait_for(state="attached", timeout=8000)
            return
        except Exception as err:
            last_err = err
            time.sleep(3)
    raise RuntimeError(f"Failed to open Customer list view: {last_err}")


def _click_new(page):
    btn = page.locator("button:has-text('New')")
    for i in range(btn.count()):
        if btn.nth(i).is_visible():
            btn.nth(i).click()
            page.locator('.o_form_view').first.wait_for(state="visible", timeout=10000)
            return
    raise RuntimeError("No visible New button found")


def _select_cust_category(page):
    """Switch to the Sales notebook tab where cust_category lives, then pick the first option."""
    page.locator("div.o_notebook a.nav-link", has_text="Sales").first.click()
    page.wait_for_timeout(500)
    page.locator('div[name="cust_category"] input').first.click()
    page.wait_for_timeout(600)
    page.locator('.o-autocomplete--dropdown-item, .o-dropdown-item').first.click()
    page.wait_for_timeout(300)


def test_customer_manual_id_required(logged_in_page):
    """Customer ID is now required manual input: saving without it must fail validation."""
    page = logged_in_page
    _goto_list(page)
    _click_new(page)

    page.locator('div[name="customer_name"] textarea, div[name="customer_name"] input').first.fill("E2E No ID Customer")
    page.locator('div[name="email"] input').first.fill(f"noid{unique_suffix()}@example.com")
    _select_cust_category(page)

    page.get_by_role("button", name="Save").first.click()
    page.wait_for_timeout(2000)

    assert page.locator('.o_form_view').count() >= 1, "Form should remain open on validation error"
    assert page.locator('div[name="customer_id"].o_field_invalid').count() >= 1 or \
        page.locator('.o_field_invalid').count() >= 1, "Expected a required-field validation error"


def test_customer_manual_id_creation(logged_in_page):
    """Create a customer entering the Customer ID manually; verify it is saved as-is."""
    page = logged_in_page
    suffix = unique_suffix()
    cust_id = f"{PREFIX}-{suffix}"

    _goto_list(page)
    _click_new(page)

    page.locator('div[name="customer_id"] input').first.fill(cust_id)
    page.locator('div[name="customer_name"] textarea, div[name="customer_name"] input').first.fill(f"E2E Manual ID Customer {suffix}")
    page.locator('div[name="email"] input').first.fill(f"manual{suffix}@example.com")
    _select_cust_category(page)

    page.get_by_role("button", name="Save").first.click()
    page.wait_for_timeout(3000)

    session = api_session()
    ids = call_kw(session, "sales.customer", "search", args=[[("customer_id", "=", cust_id)]])
    assert ids, f"Customer with ID {cust_id} was not saved"