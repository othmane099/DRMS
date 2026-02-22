import httpx

from tests.api.conftest import API, create_document, delete_document


def _ids(resp_json: dict) -> set[str]:
    return {d["id"] for d in resp_json.get("data", [])}


def _share(headers: dict, doc_id: str, user_ids: list[str], **kwargs) -> list[dict]:
    resp = httpx.post(
        f"{API}/documents/{doc_id}/share/me",
        json={"user_ids": user_ids, **kwargs},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def _revoke_share(headers: dict, doc_id: str, share_id: str) -> None:
    httpx.delete(f"{API}/documents/{doc_id}/share/{share_id}/me", headers=headers)


def _my_doc_ids(headers: dict) -> set[str]:
    resp = httpx.get(f"{API}/documents/me", params={"page_size": 100}, headers=headers)
    resp.raise_for_status()
    return _ids(resp.json())


def test_assigned_document_visible_to_assignee(
    alice_headers, bob_headers, alice, bob,
    shared_category, shared_subcategory, shared_stage,
):
    """A document created by Alice and assigned to Bob appears in Bob's /documents/me."""
    doc = create_document(
        alice_headers,
        name="Alice Doc VIS-001",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=bob["id"],
    )
    try:
        assert doc["id"] in _my_doc_ids(bob_headers)
    finally:
        delete_document(alice_headers, doc["id"])


def test_unassigned_document_not_visible_to_other_user(
    alice_headers, dave_headers, alice, bob, dave,
    shared_category, shared_subcategory, shared_stage,
):
    """A document assigned to Bob must NOT appear in Dave's /documents/me."""
    doc = create_document(
        alice_headers,
        name="Alice Doc VIS-002",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=bob["id"],
    )
    try:
        assert doc["id"] not in _my_doc_ids(dave_headers)
    finally:
        delete_document(alice_headers, doc["id"])


def test_shared_document_visible_to_shared_user(
    carol_headers, bob_headers, carol, bob,
    shared_category, shared_subcategory, shared_stage,
):
    """Carol creates doc assigned to herself, shares it with Bob → Bob sees it in /me."""
    doc = create_document(
        carol_headers,
        name="Carol Doc VIS-003",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=carol["id"],
    )
    try:
        _share(carol_headers, doc["id"], [bob["id"]])
        assert doc["id"] in _my_doc_ids(bob_headers)
    finally:
        delete_document(carol_headers, doc["id"], my=True)


def test_revoked_share_removes_document_from_shared_user(
    carol_headers, bob_headers, carol, bob,
    shared_category, shared_subcategory, shared_stage,
):
    """After Carol revokes Bob's share, Bob's /me list no longer includes the document."""
    doc = create_document(
        carol_headers,
        name="Carol Doc VIS-004",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=carol["id"],
    )
    try:
        shares = _share(carol_headers, doc["id"], [bob["id"]])
        assert doc["id"] in _my_doc_ids(bob_headers)

        _revoke_share(carol_headers, doc["id"], shares[0]["id"])
        assert doc["id"] not in _my_doc_ids(bob_headers)
    finally:
        delete_document(carol_headers, doc["id"], my=True)


def test_shared_document_visible_within_date_range(
    alice_headers, dave_headers, alice, dave,
    shared_category, shared_subcategory, shared_stage,
):
    """Alice shares doc with Dave with a valid date range; Dave sees it in /me."""
    doc = create_document(
        alice_headers,
        name="Alice Doc VIS-005",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=alice["id"],
    )
    try:
        _share(
            alice_headers,
            doc["id"],
            [dave["id"]],
            start_date="2020-01-01",
            end_date="2099-12-31",
        )
        assert doc["id"] in _my_doc_ids(dave_headers)
    finally:
        delete_document(alice_headers, doc["id"])


def test_multiple_shared_users_all_see_document(
    alice_headers, bob_headers, carol_headers, dave_headers,
    alice, bob, carol, dave,
    shared_category, shared_subcategory, shared_stage,
):
    """Alice shares one doc with Bob, Carol, Dave — all three see it in /me."""
    doc = create_document(
        alice_headers,
        name="Alice Doc VIS-006",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=alice["id"],
    )
    try:
        _share(alice_headers, doc["id"], [bob["id"], carol["id"], dave["id"]])

        for headers, name in [
            (bob_headers, "Bob"),
            (carol_headers, "Carol"),
            (dave_headers, "Dave"),
        ]:
            assert doc["id"] in _my_doc_ids(headers), (
                f"{name} should see the shared document in /documents/me"
            )
    finally:
        delete_document(alice_headers, doc["id"])
