import uuid

from playwright.sync_api import Browser, expect

from pages import RemindersPage
from tests.api.conftest import create_document, delete_document
from tests.frontend.conftest import (
    browser_login,
    create_reminder,
    delete_reminder,
)


def test_admin_sees_all_reminders(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_alice: dict,
    fe_alice_headers: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    GET /reminders returns reminders from every creator.
    Alice (MANAGER_PERMS, reminders.list) navigates to /reminders and sees
    reminders created by both Carol and herself.

    Both users create reminders on the same document (created by Carol and
    assigned to Alice, so both have it in their /me scope).
    """
    doc = create_document(
        fe_carol_headers,
        name=f"Doc FE-030 {uuid.uuid4().hex[:6]}",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_alice["id"],
    )

    subject_carol = f"Carol Admin Rem FE-030 {uuid.uuid4().hex[:6]}"
    subject_alice = f"Alice Admin Rem FE-030 {uuid.uuid4().hex[:6]}"

    rem_carol = create_reminder(fe_carol_headers, doc["id"], [fe_alice["id"]], subject_carol)
    rem_alice = create_reminder(fe_alice_headers, doc["id"], [fe_carol["id"]], subject_alice)

    ctx, page = browser_login(browser, fe_alice["username"], "Alice123!")
    try:
        pom = RemindersPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text(subject_carol)).to_be_visible()
        expect(page.get_by_text(subject_alice)).to_be_visible()
    finally:
        ctx.close()
        delete_reminder(fe_alice_headers, rem_carol["id"])
        delete_reminder(fe_alice_headers, rem_alice["id"])
        delete_document(fe_carol_headers, doc["id"], my=True)


def test_admin_updates_reminder(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_alice: dict,
    fe_alice_headers: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    Alice (reminders.update) edits a reminder from the /reminders admin page.
    The RemindersList component calls the global PUT /reminders/{id} endpoint
    (not /me), confirming the admin-scope path is exercised.

    Note: the UI shows the edit button only when the logged-in user is the
    reminder creator, so Alice creates the reminder via API then edits it.
    """
    doc = create_document(
        fe_carol_headers,
        name=f"Doc FE-031 {uuid.uuid4().hex[:6]}",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_alice["id"],
    )

    subject = f"Admin Edit FE-031 {uuid.uuid4().hex[:6]}"
    new_subject = f"Admin Edited FE-031 {uuid.uuid4().hex[:6]}"
    rem = create_reminder(fe_alice_headers, doc["id"], [fe_carol["id"]], subject)

    ctx, page = browser_login(browser, fe_alice["username"], "Alice123!")
    try:
        pom = RemindersPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        pom.click_edit(subject)
        page.wait_for_load_state("networkidle")

        page.get_by_placeholder("Enter reminder subject").fill(new_subject)
        pom.submit_update()
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text("Reminder updated successfully")).to_be_visible()
        expect(page.get_by_text(new_subject)).to_be_visible()
    finally:
        ctx.close()
        delete_reminder(fe_alice_headers, rem["id"])
        delete_document(fe_carol_headers, doc["id"], my=True)


def test_admin_deletes_reminder(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_alice: dict,
    fe_alice_headers: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    Alice (reminders.delete) deletes a reminder from the /reminders admin page.
    The RemindersList component calls the global DELETE /reminders/{id} endpoint.

    Note: edit/delete buttons appear only for the reminder creator, so Alice
    creates the reminder via API and then deletes it through the browser.
    """
    doc = create_document(
        fe_carol_headers,
        name=f"Doc FE-032 {uuid.uuid4().hex[:6]}",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_alice["id"],
    )

    subject = f"Admin Delete FE-032 {uuid.uuid4().hex[:6]}"
    rem = create_reminder(fe_alice_headers, doc["id"], [fe_carol["id"]], subject)

    ctx, page = browser_login(browser, fe_alice["username"], "Alice123!")
    try:
        pom = RemindersPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        pom.click_delete(subject)

        expect(page.get_by_role("heading", name="Delete Reminder")).to_be_visible()

        pom.confirm_delete()
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text("Reminder deleted successfully")).to_be_visible()
        expect(page.get_by_text(subject)).not_to_be_visible()
    finally:
        ctx.close()
        delete_reminder(fe_alice_headers, rem["id"])
        delete_document(fe_carol_headers, doc["id"], my=True)