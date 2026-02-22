import httpx

from tests.api.conftest import API, DUMMY_FILE, create_document, delete_document


def _create_reminder(headers: dict, doc_id: str, assign_user_ids: list[str]) -> dict:
    resp = httpx.post(
        f"{API}/documents/{doc_id}/reminders/me",
        json={
            "date": "2030-07-01",
            "time": "10:00:00",
            "subject": "Cross-Module Reminder",
            "message": "Testing cross-module integrity",
            "assign_user": assign_user_ids,
        },
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def _share(headers: dict, doc_id: str, user_ids: list[str], **kwargs) -> list[dict]:
    resp = httpx.post(
        f"{API}/documents/{doc_id}/share/me",
        json={"user_ids": user_ids, **kwargs},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def _my_doc_ids(headers: dict) -> set[str]:
    resp = httpx.get(f"{API}/documents/me", params={"page_size": 100}, headers=headers)
    resp.raise_for_status()
    return {d["id"] for d in resp.json().get("data", [])}


def _my_reminder_ids(headers: dict) -> set[str]:
    resp = httpx.get(f"{API}/reminders/me", params={"page_size": 100}, headers=headers)
    resp.raise_for_status()
    return {r["id"] for r in resp.json().get("data", [])}


def test_document_delete_cascades_to_reminders(
    alice_headers, carol_headers, alice, carol,
    shared_category, shared_subcategory, shared_stage,
):
    """Deleting a document must cascade-delete all attached reminders."""
    doc = create_document(
        alice_headers,
        name="Alice Doc CROSS-001",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=alice["id"],
    )
    doc_id = doc["id"]

    r1 = _create_reminder(alice_headers, doc_id, [alice["id"]])
    r2 = _create_reminder(alice_headers, doc_id, [carol["id"]])

    # Verify both reminders exist
    assert r1["id"] in _my_reminder_ids(alice_headers)
    assert r2["id"] in _my_reminder_ids(carol_headers)

    # Delete the document (global delete)
    del_resp = httpx.delete(f"{API}/documents/{doc_id}", headers=alice_headers)
    assert del_resp.status_code == 200

    # Both reminders must now return 404
    for headers, rid in [(alice_headers, r1["id"]), (carol_headers, r2["id"])]:
        r = httpx.get(f"{API}/reminders/{rid}/me", headers=headers)
        assert r.status_code == 404, f"Reminder {rid} should be gone after document delete"

    # Reminder IDs absent from /me lists
    assert r1["id"] not in _my_reminder_ids(alice_headers)
    assert r2["id"] not in _my_reminder_ids(carol_headers)


def test_new_version_does_not_break_share_access(
    alice_headers, bob_headers, alice, bob,
    shared_category, shared_subcategory, shared_stage,
):
    """After Alice uploads a new version, Bob (shared user) still has access."""
    doc = create_document(
        alice_headers,
        name="Alice Doc CROSS-002",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=alice["id"],
    )
    try:
        _share(alice_headers, doc["id"], [bob["id"]])

        # Upload new version
        ver_resp = httpx.post(
            f"{API}/documents/{doc['id']}/versions",
            files={"document": DUMMY_FILE},
            headers=alice_headers,
        )
        assert ver_resp.status_code == 200

        # Bob still has access
        view_resp = httpx.get(
            f"{API}/documents/{doc['id']}/me", headers=bob_headers
        )
        assert view_resp.status_code == 200
        assert view_resp.json()["id"] == doc["id"]
    finally:
        delete_document(alice_headers, doc["id"])


def test_archived_document_absent_without_filter_present_with_filter(
    alice_headers, bob_headers, alice, bob,
    shared_category, shared_subcategory, shared_stage,
):
    """After archiving, shared doc is absent without archive filter and present with it."""
    doc = create_document(
        alice_headers,
        name="Alice Doc CROSS-003",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=alice["id"],
    )
    try:
        _share(alice_headers, doc["id"], [bob["id"]])

        # Archive the document
        arch_resp = httpx.patch(
            f"{API}/documents/{doc['id']}/archive", headers=alice_headers
        )
        assert arch_resp.status_code == 200

        # Bob's /me list without filter should NOT include the archived doc
        no_filter_ids = _my_doc_ids(bob_headers)
        assert doc["id"] not in no_filter_ids

        # Bob's /me list with ?archive=true SHOULD include it
        arch_resp2 = httpx.get(
            f"{API}/documents/me",
            params={"archive": "true", "page_size": 100},
            headers=bob_headers,
        )
        arch_resp2.raise_for_status()
        arch_ids = {d["id"] for d in arch_resp2.json().get("data", [])}
        assert doc["id"] in arch_ids

        # Unarchive for cleanup
        httpx.patch(f"{API}/documents/{doc['id']}/archive", headers=alice_headers)
    finally:
        delete_document(alice_headers, doc["id"])


def test_reminder_accessible_after_document_archive(
    alice_headers, alice,
    shared_category, shared_subcategory, shared_stage,
):
    """A reminder created before document archive is still accessible after archiving."""
    doc = create_document(
        alice_headers,
        name="Alice Doc CROSS-004",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=alice["id"],
    )
    try:
        reminder = _create_reminder(alice_headers, doc["id"], [alice["id"]])

        # Archive the document
        httpx.patch(f"{API}/documents/{doc['id']}/archive", headers=alice_headers)

        # Reminder still accessible
        r = httpx.get(f"{API}/reminders/{reminder['id']}/me", headers=alice_headers)
        assert r.status_code == 200
        assert reminder["id"] in _my_reminder_ids(alice_headers)

        # Unarchive for cleanup
        httpx.patch(f"{API}/documents/{doc['id']}/archive", headers=alice_headers)
    finally:
        # Delete reminder first then doc
        httpx.delete(f"{API}/reminders/{reminder['id']}/me", headers=alice_headers)
        delete_document(alice_headers, doc["id"])


def test_pagination_correctness_in_my_scope(
    carol_headers, carol,
    shared_category, shared_subcategory, shared_stage,
):
    """25 documents assigned to Carol; pagination should report correct metadata."""
    docs = [
        create_document(
            carol_headers,
            name=f"Carol Pag Doc CROSS-005-{i:02d}",
            category_id=shared_category["id"],
            subcategory_id=shared_subcategory["id"],
            stage_id=shared_stage["id"],
            assigned_to=carol["id"],
        )
        for i in range(25)
    ]
    try:
        def page_data(p: int) -> dict:
            r = httpx.get(
                f"{API}/documents/me",
                params={"page": p, "page_size": 10},
                headers=carol_headers,
            )
            r.raise_for_status()
            return r.json()

        p1 = page_data(1)
        assert p1["has_next"] is True
        assert p1["has_previous"] is False
        assert p1["total_rows"] >= 25
        assert p1["total_pages"] >= 3

        p2 = page_data(2)
        assert p2["has_next"] is True
        assert p2["has_previous"] is True

        p3 = page_data(p1["total_pages"])
        assert p3["has_next"] is False
        assert p3["has_previous"] is True
    finally:
        for doc in docs:
            delete_document(carol_headers, doc["id"], my=True)


def test_unauthenticated_requests_return_401():
    """Requests with an invalid token must return 401 on protected endpoints.

    Note: sending *no* X-Session-Key header returns 422 (FastAPI required-header
    validation), so we send a clearly bogus value to exercise the auth path.
    """
    bogus_headers = {"X-Session-Key": "invalid-token-000"}
    endpoints = [
        ("GET",  f"{API}/documents"),
        ("GET",  f"{API}/documents/me"),
        ("GET",  f"{API}/reminders"),
        ("GET",  f"{API}/reminders/me"),
    ]
    for method, url in endpoints:
        resp = httpx.request(method, url, headers=bogus_headers)
        assert resp.status_code == 401, (
            f"{method} {url} returned {resp.status_code}, expected 401"
        )
