import uuid

import httpx
import pytest
from playwright.sync_api import Browser, BrowserContext, Page

from conftest import BASE_URL, SUPERUSER_USERNAME, SUPERUSER_PASSWORD
from tests.api.conftest import (
    API,
    MANAGER_PERMS,
    EMPLOYEE_PERMS,
    _create_user,
    _delete_user,
    _token,
    _headers,
)

BACKEND = "http://localhost:8000"


# ── Superuser browser context ─────────────────────────────────────────────────

@pytest.fixture
def admin_page(page: Page) -> Page:
    """Playwright Page pre-logged-in as superuser."""
    page.goto(f"{BASE_URL}/login")
    page.get_by_label("Username").fill(SUPERUSER_USERNAME)
    page.get_by_label("Password").fill(SUPERUSER_PASSWORD)
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url(f"{BASE_URL}/dashboard")
    return page


# ── Superuser API headers ─────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def api_admin_headers() -> dict[str, str]:
    tok = _token(SUPERUSER_USERNAME, SUPERUSER_PASSWORD)
    return _headers(tok)


# ── Shared resources ──────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def fe_shared_stage(api_admin_headers: dict[str, str]) -> dict:
    resp = httpx.post(
        f"{API}/stages",
        json={"title": f"fe-stage-{uuid.uuid4().hex[:6]}", "color": "#abcdef"},
        headers=api_admin_headers,
    )
    resp.raise_for_status()
    stage = resp.json()
    yield stage
    httpx.delete(f"{API}/stages/{stage['id']}", headers=api_admin_headers)


@pytest.fixture(scope="session")
def fe_shared_category(api_admin_headers: dict[str, str]) -> dict:
    resp = httpx.post(
        f"{API}/categories",
        json={"title": f"fe-cat-{uuid.uuid4().hex[:6]}"},
        headers=api_admin_headers,
    )
    resp.raise_for_status()
    cat = resp.json()
    yield cat
    httpx.delete(f"{API}/categories/{cat['id']}", headers=api_admin_headers)


@pytest.fixture(scope="session")
def fe_shared_subcategory(
    api_admin_headers: dict[str, str],
    fe_shared_category: dict,
) -> dict:
    resp = httpx.post(
        f"{API}/subcategories",
        json={
            "title": f"fe-sub-{uuid.uuid4().hex[:6]}",
            "category_id": fe_shared_category["id"],
        },
        headers=api_admin_headers,
    )
    resp.raise_for_status()
    sub = resp.json()
    yield sub
    httpx.delete(f"{API}/subcategories/{sub['id']}", headers=api_admin_headers)


# ── Test users ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def fe_carol(api_admin_headers: dict[str, str]) -> dict:
    """Employee-scope user: can create/manage only their own documents."""
    user = _create_user(
        api_admin_headers,
        username=f"fecarol_{uuid.uuid4().hex[:4]}",
        password="Carol123!",
        perms=EMPLOYEE_PERMS,
    )
    yield user
    _delete_user(api_admin_headers, user["id"])


@pytest.fixture(scope="session")
def fe_carol_headers(fe_carol: dict) -> dict[str, str]:
    tok = _token(fe_carol["username"], "Carol123!")
    return _headers(tok)


@pytest.fixture(scope="session")
def fe_alice(api_admin_headers: dict[str, str]) -> dict:
    """Manager-scope user: full global + my permissions."""
    user = _create_user(
        api_admin_headers,
        username=f"fealice_{uuid.uuid4().hex[:4]}",
        password="Alice123!",
        perms=MANAGER_PERMS,
    )
    yield user
    _delete_user(api_admin_headers, user["id"])


@pytest.fixture(scope="session")
def fe_alice_headers(fe_alice: dict) -> dict[str, str]:
    tok = _token(fe_alice["username"], "Alice123!")
    return _headers(tok)


# ── Browser context helper ────────────────────────────────────────────────────

def browser_login(browser: Browser, username: str, password: str) -> tuple[BrowserContext, Page]:
    """Return an isolated browser context with the given user logged in."""
    ctx = browser.new_context(base_url=BASE_URL)
    page = ctx.new_page()
    page.goto(f"{BASE_URL}/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url(f"{BASE_URL}/dashboard")
    return ctx, page