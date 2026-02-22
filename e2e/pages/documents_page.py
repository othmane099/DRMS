from playwright.sync_api import Page, Locator

from pages.base_page import BasePage


class DocumentsPage(BasePage):
    URL = "/documents"

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def goto(self) -> None:
        self.page.goto(self.URL)

    # ── Locators ───────────────────────────────────────────────────────────────

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search documents...")

    @property
    def category_select(self) -> Locator:
        """First <select> in the filter bar — the category dropdown."""
        return self.page.locator("select").first

    @property
    def archive_select(self) -> Locator:
        """Third <select> in the filter bar — the archive toggle dropdown."""
        return self.page.locator("select").nth(2)

    # ── Actions ────────────────────────────────────────────────────────────────

    def search(self, query: str) -> None:
        """Fill the search box; the 300 ms debounce fires automatically."""
        self.search_input.fill(query)

    def select_category(self, title: str) -> None:
        """Choose a category by its display title in the category dropdown."""
        self.category_select.select_option(label=title)

    def select_archive(self, label: str) -> None:
        """Choose an archive filter option by label ('Active Only' or 'Archived Only')."""
        self.archive_select.select_option(label=label)

    def click_row(self, name: str) -> None:
        """Click the document name button in the table row to open the detail page."""
        self.page.get_by_role("button", name=name, exact=True).click()

    def open_create_modal(self) -> None:
        """Click the 'Add Document' button to open the create form modal."""
        self.page.get_by_role("button", name="Add Document").click()


class MyDocumentsPage(DocumentsPage):
    URL = "/my-documents"

    def __init__(self, page: Page) -> None:
        super().__init__(page)