from playwright.sync_api import Locator, Page

from pages.base_page import BasePage


class RemindersPage(BasePage):
    def __init__(self, page: Page, url: str = "/reminders") -> None:
        super().__init__(page)
        self.URL = url

    def goto(self) -> None:
        self.page.goto(self.URL)

    # ── Locators ────────────────────────────────────────────────────────────────

    def row(self, subject: str) -> Locator:
        """Locate the table row that contains the given reminder subject."""
        return self.page.locator("tbody tr").filter(has_text=subject)

    # ── Actions ─────────────────────────────────────────────────────────────────

    def click_edit(self, subject: str) -> None:
        """Click the edit icon in the row for the given reminder subject."""
        self.row(subject).get_by_title("Edit reminder").click()

    def click_delete(self, subject: str) -> None:
        """Click the delete icon in the row for the given reminder subject."""
        self.row(subject).get_by_title("Delete reminder").click()

    def confirm_delete(self) -> None:
        """Click 'Delete Reminder' in the confirmation dialog."""
        self.page.get_by_role("button", name="Delete Reminder", exact=True).click()

    def submit_update(self) -> None:
        """JS-click 'Update Reminder' to bypass the xl-modal viewport overflow."""
        self.page.get_by_role("button", name="Update Reminder").evaluate("el => el.click()")


class MyRemindersPage(RemindersPage):
    def __init__(self, page: Page) -> None:
        super().__init__(page, url="/my-reminders")