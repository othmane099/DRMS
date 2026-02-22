from playwright.sync_api import Page, Locator

from pages.base_page import BasePage


class DashboardPage(BasePage):
    URL = "/dashboard"

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def goto(self) -> None:
        self.page.goto(self.URL)
