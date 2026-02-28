import httpx

from tests.api.conftest import (
    API,
    DUMMY_FILE,
    create_document,
    delete_document,
)


def test_carol_cannot_update_other_user_document(
    alice_headers, carol_headers, alice, carol,
    shared_category, shared_subcategory, shared_stage,
):
    """Carol (my-only) cannot update a document created by Alice."""
    doc = create_document(
        alice_headers,
        name="Alice Doc PERM-001",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=alice["id"],
    )
    try:
        resp = httpx.put(
            f"{API}/documents/{doc['id']}/me",
            json={
                "name": "hacked name",
                "category_id": shared_category["id"],
                "subcategory_id": shared_subcategory["id"],
                "stage_id": shared_stage["id"],
                "assigned_to": carol["id"],
            },
            headers=carol_headers,
        )
        assert resp.status_code == 404
    finally:
        delete_document(alice_headers, doc["id"])


def test_carol_cannot_delete_other_user_document(
    alice_headers, carol_headers, alice,
    shared_category, shared_subcategory, shared_stage,
):
    """Carol (my-only) cannot delete a document created by Alice."""
    doc = create_document(
        alice_headers,
        name="Alice Doc PERM-002",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=alice["id"],
    )
    try:
        resp = httpx.delete(f"{API}/documents/{doc['id']}/me", headers=carol_headers)
        assert resp.status_code == 404
    finally:
        delete_document(alice_headers, doc["id"])


def test_carol_cannot_archive_other_user_document(
    alice_headers, carol_headers, alice,
    shared_category, shared_subcategory, shared_stage,
):
    """Carol (my-only) cannot archive a document created by Alice."""
    doc = create_document(
        alice_headers,
        name="Alice Doc PERM-003",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=alice["id"],
    )
    try:
        resp = httpx.patch(
            f"{API}/documents/{doc['id']}/archive/me", headers=carol_headers
        )
        assert resp.status_code in (403, 404)
    finally:
        delete_document(alice_headers, doc["id"])


def test_carol_cannot_create_version_for_other_user_document(
    alice_headers, carol_headers, alice,
    shared_category, shared_subcategory, shared_stage,
):
    """Carol (my-only) cannot upload a new version for a document she does not own."""
    doc = create_document(
        alice_headers,
        name="Alice Doc PERM-004",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=alice["id"],
    )
    try:
        resp = httpx.post(
            f"{API}/documents/{doc['id']}/versions/me",
            files={"document": DUMMY_FILE},
            headers=carol_headers,
        )
        assert resp.status_code in (403, 404)
    finally:
        delete_document(alice_headers, doc["id"])


def test_bob_cannot_create_document(
    bob_headers, bob,
    shared_category, shared_subcategory, shared_stage,
):
    """Bob has no documents.create — POST must return 403."""
    resp = httpx.post(
        f"{API}/documents",
        data={
            "name": "Bob's Forbidden Doc",
            "category_id": shared_category["id"],
            "subcategory_id": shared_subcategory["id"],
            "stage_id": shared_stage["id"],
            "assigned_to": bob["id"],
        },
        files={"document": DUMMY_FILE},
        headers=bob_headers,
    )
    assert resp.status_code == 403


def test_dave_cannot_delete_document(
    alice_headers, dave_headers, alice,
    shared_category, shared_subcategory, shared_stage,
):
    """Dave (read-only) gets 403 on DELETE /documents/{id}/me."""
    doc = create_document(
        alice_headers,
        name="Alice Doc PERM-006-del",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=alice["id"],
    )
    try:
        resp = httpx.delete(f"{API}/documents/{doc['id']}/me", headers=dave_headers)
        assert resp.status_code == 403
    finally:
        delete_document(alice_headers, doc["id"])


def test_dave_cannot_update_document(
    alice_headers, dave_headers, alice,
    shared_category, shared_subcategory, shared_stage,
):
    """Dave (read-only) gets 403 on PUT /documents/{id}/me."""
    doc = create_document(
        alice_headers,
        name="Alice Doc PERM-006-upd",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=alice["id"],
    )
    try:
        resp = httpx.put(
            f"{API}/documents/{doc['id']}/me",
            json={
                "name": "Hacked",
                "category_id": shared_category["id"],
                "subcategory_id": shared_subcategory["id"],
                "stage_id": shared_stage["id"],
                "assigned_to": alice["id"],
            },
            headers=dave_headers,
        )
        assert resp.status_code == 403
    finally:
        delete_document(alice_headers, doc["id"])


def test_global_vs_my_scope_counts(
    alice_headers, admin_headers, alice,
    shared_category, shared_subcategory, shared_stage,
):
    """Alice's global list has more docs; her /me list is a subset."""
    # Create 3 docs owned by Alice
    alice_docs = [
        create_document(
            alice_headers,
            name=f"Alice My Doc PERM-010-{i}",
            category_id=shared_category["id"],
            subcategory_id=shared_subcategory["id"],
            stage_id=shared_stage["id"],
            assigned_to=alice["id"],
        )
        for i in range(3)
    ]
    # Create 1 doc owned by admin (not Alice)
    admin_doc = create_document(
        admin_headers,
        name="Admin Doc PERM-010",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=alice["id"],  # assigned to alice but NOT created by alice
    )

    try:
        global_resp = httpx.get(
            f"{API}/documents",
            params={"page_size": 100},
            headers=alice_headers,
        )
        my_resp = httpx.get(
            f"{API}/documents/me",
            params={"page_size": 100},
            headers=alice_headers,
        )
        assert global_resp.status_code == 200
        assert my_resp.status_code == 200

        global_ids = {d["id"] for d in global_resp.json()["data"]}
        my_ids = {d["id"] for d in my_resp.json()["data"]}

        # All Alice docs are in both lists
        for doc in alice_docs:
            assert doc["id"] in global_ids
            assert doc["id"] in my_ids

        # Admin doc is in global but may or may not be in my (depends on assign logic)
        assert admin_doc["id"] in global_ids
    finally:
        for doc in alice_docs:
            delete_document(alice_headers, doc["id"])
        delete_document(admin_headers, admin_doc["id"])


def test_carol_global_endpoints_return_403(carol_headers):
    """Carol has only my-scope permissions; global document endpoints must return 403."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    endpoints = [
        ("GET",    f"{API}/documents"),
        ("GET",    f"{API}/documents/{fake_id}"),
        ("DELETE", f"{API}/documents/{fake_id}"),
        ("PUT",    f"{API}/documents/{fake_id}"),
        ("PATCH",  f"{API}/documents/{fake_id}/archive"),
    ]
    for method, url in endpoints:
        resp = httpx.request(method, url, headers=carol_headers)
        assert resp.status_code == 403, (
            f"{method} {url} returned {resp.status_code}, expected 403"
        )
