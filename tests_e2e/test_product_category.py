import pytest

from .config import BASE_URL, TIMEOUT, unique_suffix
from .helpers import api_session, call_kw, cleanup_model


PREFIX = "E2E-Cat"


@pytest.fixture(autouse=True)
def _cleanup():
    """Remove any test categories left behind."""
    yield
    session = api_session()
    cleanup_model(
        session, "sales.product_category",
        [("category_name", "like", f"{PREFIX}%")],
    )


def _goto_category_list(page):
    page.goto(f"{BASE_URL}/web#menu_id=225&action=262", timeout=TIMEOUT, wait_until="commit")
    page.wait_for_timeout(4000)


def _click_new(page):
    btn = page.locator("button:has-text('New')")
    for i in range(btn.count()):
        if btn.nth(i).is_visible():
            btn.nth(i).click()
            return
    raise RuntimeError("No visible New button found")


def test_create_category_with_new_fields(logged_in_page):
    """Create a category with Product Type, Parent Category, and Description."""
    page = logged_in_page
    suffix = unique_suffix()
    parent_name = f"{PREFIX}-Parent-{suffix}"
    child_name = f"{PREFIX}-Child-{suffix}"

    # 1. Create parent category
    _goto_category_list(page)
    _click_new(page)
    page.wait_for_timeout(2000)
    page.locator('div[name="category_name"] textarea').first.fill(parent_name)
    page.locator('div[name="product_type"] input').first.click()
    page.wait_for_timeout(500)
    page.locator('.o-autocomplete--dropdown-item, .o-dropdown-item').first.click()
    page.wait_for_timeout(500)
    page.get_by_role("button", name="Save").first.click()
    page.wait_for_timeout(3000)

    # 2. Create child category with Parent Category
    _goto_category_list(page)
    _click_new(page)
    page.wait_for_timeout(2000)
    page.locator('div[name="category_name"] textarea').first.fill(child_name)
    page.locator('div[name="product_type"] input').first.click()
    page.wait_for_timeout(500)
    page.locator('.o-autocomplete--dropdown-item, .o-dropdown-item').first.click()
    page.wait_for_timeout(500)
    page.locator('div[name="parent_category_id"] input').first.click()
    page.wait_for_timeout(500)
    page.locator('.o-autocomplete--dropdown-item, .o-dropdown-item').first.click()
    page.wait_for_timeout(500)
    page.locator('div[name="description"] textarea').first.fill("Test description")
    page.wait_for_timeout(300)
    page.get_by_role("button", name="Save").first.click()
    page.wait_for_timeout(3000)

    # 3. Verify in list
    _goto_category_list(page)
    assert child_name in page.content() or page.locator(f'text="{child_name}"').count() > 0
