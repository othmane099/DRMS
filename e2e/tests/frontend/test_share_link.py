import json
import uuid
from base64 import urlsafe_b64encode
from datetime import date, timedelta

import httpx
from cryptography.fernet import Fernet
from playwright.sync_api import Browser, expect

from pages import MyDocumentsPage
from tests.api.conftest import API, create_document, delete_document
from tests.frontend.conftest import BASE_URL, browser_login

# Default key from backend/src/config.py (used when .env does not override it).
_SHARE_LINK_SECRET_KEY = "uifncAbVYX19EKKpF6HBUAmDerMY52r4ggx0gXAujrM="


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_share_link(headers: dict, document_id: str, *, password: str, expiration_date: str) -> dict:
    """POST /documents/{id}/share-link/me and return the response JSON."""
    resp = httpx.post(
        f"{API}/documents/{document_id}/share-link/me",
        json={"password": password, "expiration_date": expiration_date},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def _forge_expired_token(document_id: str) -> str:
    """
    Create a Fernet-encrypted share token whose expiration date is in the past.
    The backend rejects past-date tokens on creation, so we forge one directly
    using the same key and format the backend uses.
    """
    fernet = Fernet(_SHARE_LINK_SECRET_KEY.encode())
    payload = json.dumps({
        "document_id": document_id,
        "exp_date": (date.today() - timedelta(days=1)).isoformat(),
    }).encode()
    encrypted = fernet.encrypt(payload)
    return urlsafe_b64encode(encrypted).decode()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_share_link_with_password_and_expiration(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    Carol (documents.share_my) opens the Share Link modal for her document,
    fills in a password and an expiration date, and generates the link.

    1. The success screen is shown inside the modal with the generated URL.
    2. A new unauthenticated browser context (no session) navigates to that URL.
    3. Because the link is password-protected, the share page shows
       "Password Required".
    4. After entering the correct password the document loads successfully
       (no error message is displayed).
    """
    doc = create_document(
        fe_carol_headers,
        name=f"FE-Share-040 {uuid.uuid4().hex[:6]}",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_carol["id"],
    )

    expiration_date = (date.today() + timedelta(days=30)).isoformat()
    share_password = "ShareP@ss1"

    ctx, page = browser_login(browser, fe_carol["username"], "Carol123!")
    share_url = None
    try:
        pom = MyDocumentsPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        pom.click_share(doc["name"])

        expect(page.get_by_role("heading", name="Generate Share Link")).to_be_visible()

        pom.generate_share_link(expiration_date=expiration_date, password=share_password)
        page.wait_for_load_state("networkidle")

        expect(page.get_by_role("heading", name="Share Link Generated")).to_be_visible()

        share_url = pom.get_share_url()
        assert share_url and "/share/" in share_url, f"Unexpected share URL: {share_url!r}"

    finally:
        ctx.close()

    # ── Unauthenticated access (user without any system permissions) ──────────

    anon_ctx = browser.new_context()  # no stored session / credentials
    anon_page = anon_ctx.new_page()
    try:
        anon_page.goto(share_url)
        anon_page.wait_for_load_state("networkidle")

        # The page should ask for a password, not grant immediate access.
        expect(anon_page.get_by_role("heading", name="Password Required")).to_be_visible()
        expect(anon_page.get_by_text("This document is password-protected")).to_be_visible()

        # Enter the correct password and submit.
        anon_page.get_by_label("Password").fill(share_password)
        anon_page.get_by_role("button", name="View Document").click()
        anon_page.wait_for_load_state("networkidle")

        # The document loads — no error heading should appear.
        expect(anon_page.get_by_role("heading", name="Unable to Load Document")).not_to_be_visible()
        expect(anon_page.get_by_role("heading", name="Password Required")).not_to_be_visible()

    finally:
        anon_ctx.close()
        delete_document(fe_carol_headers, doc["id"], my=True)


def test_share_link_wrong_password_shows_error(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    A share link with password protection rejects an incorrect password.

    Carol generates a share link with a password via the UI.
    An unauthenticated visitor enters the wrong password and the page shows
    "Invalid password or link has expired".
    """
    doc = create_document(
        fe_carol_headers,
        name=f"FE-Share-041 {uuid.uuid4().hex[:6]}",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_carol["id"],
    )

    share_password = "CorrectP@ss1"
    expiration_date = (date.today() + timedelta(days=7)).isoformat()

    # Generate the share link via API to avoid duplicating UI interaction.
    share_resp = _generate_share_link(
        fe_carol_headers,
        doc["id"],
        password=share_password,
        expiration_date=expiration_date,
    )
    token = share_resp["token"]
    share_url = f"{BASE_URL}/share/{token}"

    anon_ctx = browser.new_context()
    anon_page = anon_ctx.new_page()
    try:
        anon_page.goto(share_url)
        anon_page.wait_for_load_state("networkidle")

        expect(anon_page.get_by_role("heading", name="Password Required")).to_be_visible()

        # Enter the wrong password.
        anon_page.get_by_label("Password").fill("WrongPass!")
        anon_page.get_by_role("button", name="View Document").click()
        anon_page.wait_for_load_state("networkidle")

        # The page should show an error — the form stays visible.
        expect(anon_page.get_by_text("Invalid password or link has expired")).to_be_visible()

    finally:
        anon_ctx.close()
        delete_document(fe_carol_headers, doc["id"], my=True)


def test_expired_share_link_shows_error(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    Navigating to a share link whose expiration date is in the past shows
    the "Unable to Load Document" error screen with the message
    "Invalid password or link has expired".

    Because the backend validates the expiration date on creation (rejecting
    past dates), the expired token is forged locally using the same Fernet key
    and payload format the backend uses.
    """
    doc = create_document(
        fe_carol_headers,
        name=f"FE-Share-042 {uuid.uuid4().hex[:6]}",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_carol["id"],
    )

    expired_token = _forge_expired_token(doc["id"])
    share_url = f"{BASE_URL}/share/{expired_token}"

    anon_ctx = browser.new_context()
    anon_page = anon_ctx.new_page()
    try:
        anon_page.goto(share_url)
        anon_page.wait_for_load_state("networkidle")

        # The error screen (not the password form) should be displayed.
        expect(anon_page.get_by_role("heading", name="Unable to Load Document")).to_be_visible()
        expect(anon_page.get_by_text("Invalid password or link has expired")).to_be_visible()

        # The password form must not appear — the link is simply expired.
        expect(anon_page.get_by_role("heading", name="Password Required")).not_to_be_visible()

    finally:
        anon_ctx.close()
        delete_document(fe_carol_headers, doc["id"], my=True)