from playwright.sync_api import Page

from pages.base_page import BasePage


class RemindersPage(BasePage):
    def __init__(self, page: Page, url: str = "/reminders") -> None:
        super().__init__(page)
        self.URL = url

    def goto(self) -> None:
        self.page.goto(self.URL)


class MyRemindersPage(RemindersPage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, url="/my-reminders")