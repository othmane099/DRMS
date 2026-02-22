from playwright.sync_api import Page, Locator


class LoginPage:
    URL = "/login"

    def __init__(self, page: Page) -> None:
        self.page = page

    def goto(self) -> None:
        self.page.goto(self.URL)

    # ── Locators ───────────────────────────────────────────────────────────────

    @property
    def username_input(self) -> Locator:
        return self.page.get_by_label("Username")

    @property
    def password_input(self) -> Locator:
        return self.page.get_by_label("Password")

    @property
    def submit_button(self) -> Locator:
        return self.page.get_by_role("button", name="Sign in")

    @property
    def error_message(self) -> Locator:
        return self.page.locator(".bg-red-50")

    # ── Actions ────────────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> None:
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.submit_button.click()