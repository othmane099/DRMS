import os
import tempfile
import uuid

import httpx
from playwright.sync_api import Browser, expect

from pages import DocumentsPage, MyDocumentsPage
from tests.api.conftest import API, create_document, delete_document
from tests.frontend.conftest import browser_login


def test_carol_sees_only_her_documents(
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
    GET /documents/me returns only documents Carol created or was assigned to.
    Alice's document (assigned to Alice) must not appear in Carol's list.
    """
    carol_doc = create_document(
        fe_carol_headers,
        name="Carol FE-001",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_carol["id"],
    )
    alice_doc = create_document(
        fe_alice_headers,
        name="Alice FE-001",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_alice["id"],
    )

    ctx, page = browser_login(browser, fe_carol["username"], "Carol123!")
    try:
        pom = MyDocumentsPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text(carol_doc["name"])).to_be_visible()
        expect(page.get_by_text(alice_doc["name"])).not_to_be_visible()
    finally:
        ctx.close()
        delete_document(fe_carol_headers, carol_doc["id"], my=True)
        delete_document(fe_alice_headers, alice_doc["id"], my=True)


def test_search_filters_documents(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    Typing in the search box sends ?search=<query> to GET /documents/me.
    Only matching documents remain visible; unrelated ones disappear.
    """
    doc_match = create_document(
        fe_carol_headers,
        name="Carol Report FE-002",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_carol["id"],
    )
    doc_other = create_document(
        fe_carol_headers,
        name="Carol Summary FE-002",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_carol["id"],
    )

    ctx, page = browser_login(browser, fe_carol["username"], "Carol123!")
    try:
        pom = MyDocumentsPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        # Both documents visible before searching
        expect(page.get_by_text(doc_match["name"])).to_be_visible()
        expect(page.get_by_text(doc_other["name"])).to_be_visible()

        pom.search("Report")
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text(doc_match["name"])).to_be_visible()
        expect(page.get_by_text(doc_other["name"])).not_to_be_visible()
    finally:
        ctx.close()
        delete_document(fe_carol_headers, doc_match["id"], my=True)
        delete_document(fe_carol_headers, doc_other["id"], my=True)


def test_category_filter_narrows_list(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    api_admin_headers: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    Selecting a category in the filter dropdown sends ?category_id=… to
    GET /documents/me.  Only documents in the selected category remain
    visible; documents in other categories disappear.
    """
    # Create a second category (and a matching subcategory) for this test only.
    cat_b_resp = httpx.post(
        f"{API}/categories",
        json={"title": f"fe-cat-b-{uuid.uuid4().hex[:6]}"},
        headers=api_admin_headers,
    )
    cat_b_resp.raise_for_status()
    cat_b = cat_b_resp.json()

    sub_b_resp = httpx.post(
        f"{API}/subcategories",
        json={"title": f"fe-sub-b-{uuid.uuid4().hex[:6]}", "category_id": cat_b["id"]},
        headers=api_admin_headers,
    )
    sub_b_resp.raise_for_status()
    sub_b = sub_b_resp.json()

    doc_a = create_document(
        fe_carol_headers,
        name="Carol Cat-A FE-003",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_carol["id"],
    )
    doc_b = create_document(
        fe_carol_headers,
        name="Carol Cat-B FE-003",
        category_id=cat_b["id"],
        subcategory_id=sub_b["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_carol["id"],
    )

    ctx, page = browser_login(browser, fe_carol["username"], "Carol123!")
    try:
        pom = MyDocumentsPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        # Both documents visible before filtering.
        expect(page.get_by_text(doc_a["name"])).to_be_visible()
        expect(page.get_by_text(doc_b["name"])).to_be_visible()

        # Select the shared category — only doc_a should remain.
        pom.select_category(fe_shared_category["title"])
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text(doc_a["name"])).to_be_visible()
        expect(page.get_by_text(doc_b["name"])).not_to_be_visible()
    finally:
        ctx.close()
        delete_document(fe_carol_headers, doc_a["id"], my=True)
        delete_document(fe_carol_headers, doc_b["id"], my=True)
        httpx.delete(f"{API}/subcategories/{sub_b['id']}", headers=api_admin_headers)
        httpx.delete(f"{API}/categories/{cat_b['id']}", headers=api_admin_headers)


def test_archive_toggle_shows_archived_documents(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    The default view ('Active Only') hides archived documents.
    Switching the archive filter to 'Archived Only' sends ?archive=true;
    active documents disappear and archived ones become visible.
    """
    doc_active = create_document(
        fe_carol_headers,
        name="Carol Active FE-004",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_carol["id"],
    )
    doc_archived = create_document(
        fe_carol_headers,
        name="Carol Archived FE-004",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_carol["id"],
    )
    # Archive the second document via API.
    httpx.patch(
        f"{API}/documents/{doc_archived['id']}/archive/me",
        headers=fe_carol_headers,
    ).raise_for_status()

    ctx, page = browser_login(browser, fe_carol["username"], "Carol123!")
    try:
        pom = MyDocumentsPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        # Default "Active Only": active visible, archived hidden.
        expect(page.get_by_text(doc_active["name"])).to_be_visible()
        expect(page.get_by_text(doc_archived["name"])).not_to_be_visible()

        # Switch to "Archived Only": archived visible, active hidden.
        pom.select_archive("Archived Only")
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text(doc_archived["name"])).to_be_visible()
        expect(page.get_by_text(doc_active["name"])).not_to_be_visible()
    finally:
        ctx.close()
        # Unarchive before deleting so delete_my succeeds.
        httpx.patch(
            f"{API}/documents/{doc_archived['id']}/archive/me",
            headers=fe_carol_headers,
        )
        delete_document(fe_carol_headers, doc_active["id"], my=True)
        delete_document(fe_carol_headers, doc_archived["id"], my=True)


def test_clicking_row_navigates_to_detail(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    Clicking the document name in the list navigates to /my-documents/{id}.
    The DocumentDetail component renders with the document's name (heading),
    category, stage, and assigned user.
    """
    doc = create_document(
        fe_carol_headers,
        name="Carol Detail FE-005",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_carol["id"],
    )

    ctx, page = browser_login(browser, fe_carol["username"], "Carol123!")
    try:
        pom = MyDocumentsPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        pom.click_row(doc["name"])
        page.wait_for_url(f"**/my-documents/{doc['id']}")
        page.wait_for_load_state("networkidle")

        # Heading and detail fields rendered by DocumentDetail.
        expect(page.get_by_role("heading", name=doc["name"])).to_be_visible()
        expect(page.get_by_text(fe_shared_category["title"])).to_be_visible()
        expect(page.get_by_text(fe_shared_stage["title"])).to_be_visible()
        expect(page.get_by_text(fe_carol["username"]).first).to_be_visible()
    finally:
        ctx.close()
        delete_document(fe_carol_headers, doc["id"], my=True)


def test_create_document_form_submits_correctly(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_alice: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    Filling the create-document form and submitting it calls POST /documents,
    shows a success toast, closes the modal, and adds the document to the list.
    """
    doc_name = f"FE-008 Created {uuid.uuid4().hex[:6]}"
    tmp_file = None

    ctx, page = browser_login(browser, fe_carol["username"], "Carol123!")
    try:
        pom = MyDocumentsPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        pom.open_create_modal()

        # Scope all form interactions to the <form> element (unique when modal is open).
        form = page.locator("form")
        page.wait_for_load_state("networkidle")  # dropdown data loaded

        # Document name.
        page.get_by_label("Document Name").fill(doc_name)

        # File upload — Playwright requires a real path on disk.
        fd, tmp_file = tempfile.mkstemp(suffix=".txt")
        os.write(fd, b"dummy content for e2e test")
        os.close(fd)
        form.locator('input[type="file"]').set_input_files(tmp_file)

        # Category (triggers async subcategory fetch).
        form.locator("select").nth(0).select_option(label=fe_shared_category["title"])
        page.wait_for_load_state("networkidle")

        # Subcategory (enabled once category is selected).
        form.locator("select").nth(1).select_option(label=fe_shared_subcategory["title"])

        # Stage.
        form.locator("select").nth(2).select_option(label=fe_shared_stage["title"])

        # Assign to Alice.
        form.locator("select").nth(3).select_option(label=fe_alice["username"])

        form.get_by_role("button", name="Create Document").click()

        # Success toast appears.
        expect(page.get_by_text("Document created successfully")).to_be_visible()

        page.wait_for_load_state("networkidle")

        # New document appears in the refreshed list.
        expect(page.get_by_text(doc_name)).to_be_visible()
    finally:
        ctx.close()
        if tmp_file:
            os.unlink(tmp_file)
        # Locate the created document via API and delete it.
        resp = httpx.get(
            f"{API}/documents/me",
            params={"search": doc_name, "page_size": 5},
            headers=fe_carol_headers,
        )
        if resp.status_code == 200:
            for doc in resp.json().get("data", []):
                if doc["name"] == doc_name:
                    delete_document(fe_carol_headers, doc["id"], my=True)
                    break


def test_assigned_user_sees_document_in_my_documents(
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
    Carol creates a document assigned to Alice.
    Alice opens /my-documents and the document is present in her list.
    """
    doc = create_document(
        fe_carol_headers,
        name="Carol Assigns Alice FE-011",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_alice["id"],
    )

    ctx, page = browser_login(browser, fe_alice["username"], "Alice123!")
    try:
        pom = MyDocumentsPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text(doc["name"])).to_be_visible()
    finally:
        ctx.close()
        # Carol created it so she (or Alice with global delete) can delete it.
        delete_document(fe_carol_headers, doc["id"], my=True)


def test_admin_documents_list_shows_all_users(
    browser: Browser,
    fe_carol: dict,
    fe_carol_headers: dict,
    fe_alice: dict,
    fe_shared_category: dict,
    fe_shared_subcategory: dict,
    fe_shared_stage: dict,
):
    """
    A user with documents.list (global scope) navigates to /documents and sees
    documents created by other users — not just their own.
    Carol creates two documents; Alice (MANAGER_PERMS, documents.list) views
    the global list and both documents are visible.
    """
    doc1 = create_document(
        fe_carol_headers,
        name="Carol Global-1 FE-012",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_carol["id"],
    )
    doc2 = create_document(
        fe_carol_headers,
        name="Carol Global-2 FE-012",
        category_id=fe_shared_category["id"],
        subcategory_id=fe_shared_subcategory["id"],
        stage_id=fe_shared_stage["id"],
        assigned_to=fe_alice["id"],
    )

    ctx, page = browser_login(browser, fe_alice["username"], "Alice123!")
    try:
        pom = DocumentsPage(page)
        pom.goto()
        page.wait_for_load_state("networkidle")

        # Both of Carol's documents appear in Alice's global list.
        expect(page.get_by_text(doc1["name"])).to_be_visible()
        expect(page.get_by_text(doc2["name"])).to_be_visible()
    finally:
        ctx.close()
        delete_document(fe_carol_headers, doc1["id"], my=True)
        delete_document(fe_carol_headers, doc2["id"], my=True)
