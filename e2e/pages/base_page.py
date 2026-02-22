from playwright.sync_api import Page, Locator


class BasePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    # ── Sidebar ────────────────────────────────────────────────────────────────

    def click_nav_link(self, name: str) -> None:
        """Click a sidebar navigation link by its visible text."""
        self.page.locator("aside nav").get_by_role("link", name=name, exact=True).click()

    def goto_dashboard(self) -> None:
        self.page.locator("aside nav").get_by_role("link", name="Dashboard", exact=True).click()

    # ── Header user menu ───────────────────────────────────────────────────────

    def open_user_menu(self) -> None:
        self.page.locator("header button").click()

    def logout(self) -> None:
        self.open_user_menu()
        self.page.get_by_role("button", name="Logout").click()

    def open_change_password(self) -> None:
        self.open_user_menu()
        self.page.get_by_role("button", name="Change Password").click()

    # ── Shared helpers ─────────────────────────────────────────────────────────

    @property
    def toast(self) -> Locator:
        return self.page.locator("[role='status']")