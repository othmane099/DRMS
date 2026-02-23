import uuid

import httpx
from playwright.sync_api import Browser, expect

from pages import MyRemindersPage
from tests.api.conftest import API, create_document, delete_document
from tests.frontend.conftest import (
    browser_login,
    create_reminder,
    delete_reminder,
    delete_reminder_me,
)


def test_carol_sees_only_her_reminders_on_load(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_alice: dict,
    fe_alice_headers: dict,
    api_admin_headers: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    GET /reminders/me returns reminders where the user is creator OR assignee.
    Carol must not see a reminder where she is neither.

    - Alice creates rem_carol assigned to Carol → Carol sees it (she's assignee).
    - Alice creates rem_other assigned to a temp third user → Carol can't see it
      (she's neither creator nor assignee).

    The document is created by Carol (assigned to Alice) so both users have it
    in their /me scope for reminder creation.
    """
    # A temporary user to serve as the sole assignee of the "invisible" reminder.
    third_resp = httpx.post(
        f"{API}/users",
        json={
            "first_name": "Third",
            "last_name": "E2E",
            "username": f"fethird_{uuid.uuid4().hex[:6]}",
            "password": "Third123!",
            "is_active": True,
            "role_id": None,
        },
        headers=api_admin_headers,
    )
    third_resp.raise_for_status()
    third_user = third_resp.json()

    doc = create_document(
        fe_carol_headers,
        name="Carol Rem FE-020",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_alice["id"],
    )

    subject_carol = f"Carol Reminder FE-020 {uuid.uuid4().hex[:6]}"
    subject_other = f"Other Reminder FE-020 {uuid.uuid4().hex[:6]}"

    # Carol creates a reminder assigned to third_user — Carol sees it as creator.
    rem_carol = create_reminder(fe_carol_headers, doc["id"], [third_user["id"]], subject_carol)
    # Alice creates a reminder assigned to third_user — Carol is neither creator
    # nor assignee, so it must not appear in her list.
    rem_other = create_reminder(fe_alice_headers, doc["id"], [third_user["id"]], subject_other)

    ctx, page = browser_login(browser, fe_carol["username"], "Carol123!")
    try:
        pom = MyRemindersPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text(subject_carol)).to_be_visible()
        expect(page.get_by_text(subject_other)).not_to_be_visible()
    finally:
        ctx.close()
        delete_reminder(fe_alice_headers, rem_carol["id"])
        delete_reminder(fe_alice_headers, rem_other["id"])
        delete_document(fe_carol_headers, doc["id"], my=True)
        httpx.delete(f"{API}/users/{third_user['id']}", headers=api_admin_headers)


def test_reminder_row_displays_all_fields(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_alice: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    Each reminder row must render subject, document name, date, time, and the
    assigned user's username badge.

    Carol creates a document (assigned to Alice) and a reminder on it assigned
    to Alice.  Carol sees the reminder as creator; all fields are checked.
    """
    doc_name = f"Doc FE-021 {uuid.uuid4().hex[:6]}"
    doc = create_document(
        fe_carol_headers,
        name=doc_name,
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_alice["id"],
    )

    subject = f"Reminder FE-021 {uuid.uuid4().hex[:6]}"
    rem = create_reminder(fe_carol_headers, doc["id"], [fe_alice["id"]], subject)

    ctx, page = browser_login(browser, fe_carol["username"], "Carol123!")
    try:
        pom = MyRemindersPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text(subject)).to_be_visible()
        expect(page.get_by_text(doc_name)).to_be_visible()
        expect(page.get_by_text("2030-06-01")).to_be_visible()
        expect(page.get_by_text("08:00:00")).to_be_visible()
        expect(page.get_by_text(fe_alice["username"])).to_be_visible()
    finally:
        ctx.close()
        delete_reminder_me(fe_carol_headers, rem["id"])
        delete_document(fe_carol_headers, doc["id"], my=True)


def test_edit_reminder_form_pre_fills_existing_values(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_alice: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    Clicking the edit icon opens the 'Edit Reminder' modal with all form
    fields pre-populated from the existing reminder: subject, date, time,
    message, and the assigned user's checkbox checked.
    """
    doc = create_document(
        fe_carol_headers,
        name=f"Doc FE-023 {uuid.uuid4().hex[:6]}",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_alice["id"],
    )

    subject = f"Edit Prefill FE-023 {uuid.uuid4().hex[:6]}"
    rem = create_reminder(fe_carol_headers, doc["id"], [fe_alice["id"]], subject)

    ctx, page = browser_login(browser, fe_carol["username"], "Carol123!")
    try:
        pom = MyRemindersPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        pom.click_edit(subject)
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text("Edit Reminder")).to_be_visible()
        expect(page.get_by_placeholder("Enter reminder subject")).to_have_value(subject)
        expect(page.locator("input[type='date']")).to_have_value("2030-06-01")
        expect(page.locator("input[type='time']")).to_have_value("08:00:00")
        expect(page.get_by_placeholder("Enter reminder message")).to_have_value("FE test reminder")
        user_label = page.locator("label").filter(has_text=fe_alice["username"])
        expect(user_label.locator("input[type='checkbox']")).to_be_checked()
    finally:
        ctx.close()
        delete_reminder_me(fe_carol_headers, rem["id"])
        delete_document(fe_carol_headers, doc["id"], my=True)


def test_edit_reminder_saves_and_updates_list(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_alice: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    After opening the edit form, changing the date, and clicking 'Update
    Reminder', the list row reflects the new date and a success toast is shown.
    """
    doc = create_document(
        fe_carol_headers,
        name=f"Doc FE-024 {uuid.uuid4().hex[:6]}",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_alice["id"],
    )

    subject = f"Edit Save FE-024 {uuid.uuid4().hex[:6]}"
    rem = create_reminder(fe_carol_headers, doc["id"], [fe_alice["id"]], subject)

    ctx, page = browser_login(browser, fe_carol["username"], "Carol123!")
    try:
        pom = MyRemindersPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        pom.click_edit(subject)
        page.wait_for_load_state("networkidle")

        page.locator("input[type='date']").fill("2031-12-31")
        pom.submit_update()
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text("Reminder updated successfully")).to_be_visible()
        expect(pom.row(subject).get_by_text("2031-12-31")).to_be_visible()
    finally:
        ctx.close()
        delete_reminder_me(fe_carol_headers, rem["id"])
        delete_document(fe_carol_headers, doc["id"], my=True)


def test_delete_reminder_confirms_then_removes(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_alice: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    Clicking the delete icon opens a confirmation modal; confirming removes the
    reminder from the list and shows a success toast.
    """
    doc = create_document(
        fe_carol_headers,
        name=f"Doc FE-025 {uuid.uuid4().hex[:6]}",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_alice["id"],
    )

    subject = f"Delete Me FE-025 {uuid.uuid4().hex[:6]}"
    rem = create_reminder(fe_carol_headers, doc["id"], [fe_alice["id"]], subject)

    ctx, page = browser_login(browser, fe_carol["username"], "Carol123!")
    try:
        pom = MyRemindersPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        pom.click_delete(subject)

        expect(page.get_by_role("heading", name="Delete Reminder")).to_be_visible()
        expect(page.get_by_text("Are you sure you want to delete the reminder")).to_be_visible()

        pom.confirm_delete()
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text("Reminder deleted successfully")).to_be_visible()
        expect(page.get_by_text(subject)).not_to_be_visible()
    finally:
        ctx.close()
        delete_reminder_me(fe_carol_headers, rem["id"])
        delete_document(fe_carol_headers, doc["id"], my=True)


def test_assignee_sees_reminder_created_by_another_user(
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
    A reminder created by Carol and assigned to Alice must appear in Alice's
    /my-reminders list, showing both the subject and the document name.
    """
    doc_name = f"Doc FE-026 {uuid.uuid4().hex[:6]}"
    doc = create_document(
        fe_carol_headers,
        name=doc_name,
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_alice["id"],
    )

    subject = f"Assigned To Alice FE-026 {uuid.uuid4().hex[:6]}"
    rem = create_reminder(fe_carol_headers, doc["id"], [fe_alice["id"]], subject)

    ctx, page = browser_login(browser, fe_alice["username"], "Alice123!")
    try:
        pom = MyRemindersPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text(subject)).to_be_visible()
        expect(page.get_by_text(doc_name)).to_be_visible()
    finally:
        ctx.close()
        delete_reminder_me(fe_carol_headers, rem["id"])
        delete_document(fe_carol_headers, doc["id"], my=True)


def test_create_reminder_from_document_detail(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_alice: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    From the Reminders tab on a document's detail page, Carol fills the create
    form and submits it.  The success toast is shown, and the new reminder
    subsequently appears in /my-reminders.

    Document cascade-deletion in the finally block also removes the reminder,
    so no explicit reminder cleanup is needed.
    """
    doc = create_document(
        fe_carol_headers,
        name=f"Doc FE-027 {uuid.uuid4().hex[:6]}",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_alice["id"],
    )

    subject = f"New Reminder FE-027 {uuid.uuid4().hex[:6]}"

    ctx, page = browser_login(browser, fe_carol["username"], "Carol123!")
    try:
        page.goto(f"/my-documents/{doc['id']}")
        page.wait_for_load_state("networkidle")

        page.get_by_role("button", name="Reminders").click()
        page.wait_for_load_state("networkidle")

        page.get_by_role("button", name="Create Reminder").click()
        page.wait_for_load_state("networkidle")

        page.locator("input[type='date']").fill("2030-09-15")
        page.locator("input[type='time']").fill("10:30")
        page.get_by_placeholder("Enter reminder subject").fill(subject)
        page.get_by_placeholder("Enter reminder message").fill("Created from detail FE-027")

        user_label = page.locator("label").filter(has_text=fe_alice["username"])
        user_label.locator("input[type='checkbox']").check()

        # There may be multiple "Create Reminder" buttons (tab + modal submit);
        # target the last one and JS-click to bypass the xl-modal viewport overflow.
        page.get_by_role("button", name="Create Reminder").last.evaluate("el => el.click()")
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text("Reminder created successfully")).to_be_visible()

        pom = MyRemindersPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")
        expect(page.get_by_text(subject)).to_be_visible()
    finally:
        ctx.close()
        delete_document(fe_carol_headers, doc["id"], my=True)