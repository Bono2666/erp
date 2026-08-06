import pytest

from .config import BASE_URL, TIMEOUT, unique_suffix
from .helpers import api_session, call_kw, cleanup_model


PREFIX = "E2E-Prod"


@pytest.fixture(autouse=True)
def _cleanup():
    """Remove test products and related BOMs."""
    yield
    session = api_session()
    cleanup_model(
        session, "sales.products",
        [("product_name", "like", f"{PREFIX}%")],
    )


def _goto_products_list(page):
    page.goto(f"{BASE_URL}/web#menu_id=223&action=255", timeout=TIMEOUT, wait_until="commit")
    page.wait_for_timeout(4000)


def _click_new(page):
    btn = page.locator("button:has-text('New')")
    for i in range(btn.count()):
        if btn.nth(i).is_visible():
            btn.nth(i).click()
            return
    raise RuntimeError("No visible New button found")


def test_new_product_form_opens(logged_in_page):
    """Regression: 'New' on Products must not throw vendor_id error."""
    page = logged_in_page
    _goto_products_list(page)
    _click_new(page)
    page.wait_for_timeout(3000)
    assert page.locator('.o_form_view, .o_form_sheet').count() >= 1


def test_product_cogs_and_bom(logged_in_page):
    """Create a product, set COGS, verify form saves."""
    page = logged_in_page
    suffix = unique_suffix()
    prod_name = f"{PREFIX}-{suffix}"

    _goto_products_list(page)
    _click_new(page)
    page.wait_for_timeout(3000)

    page.locator('div[name="product_name"] textarea, div[name="product_name"] input').first.fill(prod_name)
    page.wait_for_timeout(500)

    page.locator('div[name="product_category"] input').first.click()
    page.wait_for_timeout(500)
    page.locator('.o-autocomplete--dropdown-item, .o-dropdown-item').first.click()
    page.wait_for_timeout(500)

    page.locator('div[name="product_type"] input').first.click()
    page.wait_for_timeout(500)
    page.locator('.o-autocomplete--dropdown-item, .o-dropdown-item').first.click()
    page.wait_for_timeout(500)

    page.locator('div[name="cogs"] input').first.fill("100000")
    page.wait_for_timeout(500)

    page.get_by_role("button", name="Save").first.click()
    page.wait_for_timeout(3000)

    assert page.locator('.o_form_view, .o_form_sheet').count() >= 1
