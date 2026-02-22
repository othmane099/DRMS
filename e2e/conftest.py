import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import pytest
from playwright.sync_api import Page

BASE_URL = "http://localhost:3000"

SUPERUSER_USERNAME = "superuser"
SUPERUSER_PASSWORD = "superuser123"


def login(page: Page, username: str, password: str) -> None:
    page.goto(f"{BASE_URL}/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url(f"{BASE_URL}/dashboard")


@pytest.fixture
def logged_in_page(page: Page) -> Page:
    login(page, SUPERUSER_USERNAME, SUPERUSER_PASSWORD)
    return page
