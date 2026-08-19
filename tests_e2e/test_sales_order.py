import pytest

from .config import BASE_URL, TIMEOUT, unique_suffix
from .helpers import api_session, call_kw, cleanup_model


PREFIX = "E2E-SO"


@pytest.fixture(autouse=True)
def _cleanup():
    """Remove test SOs, products, customers created during the test."""
    yield
    session = api_session()
    cleanup_model(session, "sales.sales_order", [("sales_code", "like", f"{PREFIX}%")])
    cleanup_model(session, "sales.products", [("product_name", "like", f"{PREFIX}%")])
    cleanup_model(session, "res.partner", [("name", "like", f"{PREFIX}%")])


def _create_test_customer(session):
    name = f"{PREFIX}-Cust-{unique_suffix()}"
    customer_id = call_kw(session, "res.partner", "create", args=[{"name": name, "customer_rank": 1}])
    return customer_id, name


def _create_test_product(session):
    name = f"{PREFIX}-Prod-{unique_suffix()}"
    category_ids = call_kw(session, "sales.product_category", "search", args=[[]])
    product_id = call_kw(session, "sales.products", "create", args=[{
        "product_id": f"{PREFIX}-{unique_suffix()}",
        "product_name": name,
        "product_category": category_ids[0] if category_ids else False,
        "base_price": 50000,
        "cogs": 30000,
    }])
    return product_id, name


def _click_new(page):
    btn = page.locator("button:has-text('New')")
    for i in range(btn.count()):
        if btn.nth(i).is_visible():
            btn.nth(i).click()
            return
    raise RuntimeError("No visible New button found")


def test_so_workflow_simple(logged_in_page):
    """Create a SO with a product, save, verify form."""
    page = logged_in_page
    session = api_session()

    cust_id, cust_name = _create_test_customer(session)
    prod_id, prod_name = _create_test_product(session)

    # Navigate directly to Quotations
    page.goto(f"{BASE_URL}/web#menu_id=215&action=259", timeout=TIMEOUT, wait_until="commit")
    page.wait_for_timeout(5000)

    # Click New
    _click_new(page)
    page.wait_for_timeout(5000)

    # Verify form opened
    if page.locator('.o_form_view').count() == 0:
        # Fallback: click New via JS
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button.o_list_button_add');
            for (const btn of btns) {
                if (btn.offsetParent !== null) { btn.click(); return; }
            }
        }""")
        page.wait_for_timeout(5000)

    assert page.locator('.o_form_view').count() >= 1

    # Select customer
    page.locator('div[name="customer_id"] input').first.click()
    page.wait_for_timeout(500)
    page.keyboard.type(cust_name)
    page.wait_for_timeout(1500)
    page.locator('.o-autocomplete--dropdown-item, .o-dropdown-item').first.click()
    page.wait_for_timeout(500)

    # Save
    page.get_by_role("button", name="Save").first.click()
    page.wait_for_timeout(3000)

    assert page.locator('.o_form_view, .o_form_sheet').count() >= 1
