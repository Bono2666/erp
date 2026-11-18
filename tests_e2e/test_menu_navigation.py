from .config import BASE_URL, TIMEOUT


def _get_app_texts(page):
    """Collect all visible app/menu label texts."""
    return [
        t.strip()
        for t in page.locator(
            ".home-menu-card, .o_menu_entry, .o_app_name, .o_nav_entry, "
            "button[class*='home-card'], a[class*='home-card']"
        ).all_text_contents()
        if t.strip()
        and len(t.strip()) < 30
        and t.strip() not in ("Home",)
    ]


def test_dashboards_hidden(logged_in_page):
    """'Dashboards' app must not appear."""
    logged_in_page.wait_for_timeout(3000)
    texts = _get_app_texts(logged_in_page)
    assert "Dashboards" not in texts


def test_apps_hidden(logged_in_page):
    """'Apps' app must not appear."""
    texts = _get_app_texts(logged_in_page)
    assert "Apps" not in texts


def test_invoicing_account_hidden(logged_in_page):
    """'Invoicing' (account) app must not appear."""
    texts = _get_app_texts(logged_in_page)
    assert "Invoicing" not in texts


def test_sales_menu_visible(logged_in_page):
    """'Sales' app must appear."""
    texts = _get_app_texts(logged_in_page)
    assert "Sales" in texts


def test_navigate_to_products(logged_in_page):
    """Click Sales app card, then navigate to Master Data > Products."""
    logged_in_page.wait_for_timeout(2000)
    logged_in_page.locator("button.home-menu-card.home-card-sales").first.click()
    logged_in_page.wait_for_timeout(5000)
    logged_in_page.locator("button.dropdown-toggle", has_text="Master Data").first.click()
    logged_in_page.locator(".dropdown-item", has_text="Products").first.click()
    logged_in_page.wait_for_timeout(3000)
    assert "model=sales.products" in logged_in_page.url
