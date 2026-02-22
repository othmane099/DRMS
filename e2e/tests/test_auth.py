from playwright.sync_api import Page, expect

from conftest import BASE_URL, SUPERUSER_USERNAME, SUPERUSER_PASSWORD
from pages import LoginPage, DashboardPage


def test_login_redirects_to_dashboard(page: Page) -> None:
    login_page = LoginPage(page)
    login_page.goto()
    login_page.login(SUPERUSER_USERNAME, SUPERUSER_PASSWORD)
    expect(page).to_have_url(f"{BASE_URL}/dashboard")


def test_login_invalid_credentials_shows_error(page: Page) -> None:
    login_page = LoginPage(page)
    login_page.goto()
    login_page.login("wronguser", "wrongpassword")
    expect(login_page.error_message).to_be_visible()


def test_unauthenticated_redirects_to_login(page: Page) -> None:
    dashboard = DashboardPage(page)
    dashboard.goto()
    expect(page).to_have_url(f"{BASE_URL}/login")


def test_logout(logged_in_page: Page) -> None:
    dashboard = DashboardPage(logged_in_page)
    dashboard.logout()
    expect(logged_in_page).to_have_url(f"{BASE_URL}/login")
