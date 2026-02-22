import httpx

from tests.api.conftest import API, create_document, delete_document


def _create_reminder(headers: dict, doc_id: str, assign_user_ids: list[str]) -> dict:
    resp = httpx.post(
        f"{API}/documents/{doc_id}/reminders/me",
        json={
            "date": "2030-06-01",
            "time": "08:00:00",
            "subject": "E2E Visibility Reminder",
            "message": "Reminder for visibility testing",
            "assign_user": assign_user_ids,
        },
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def _delete_reminder(admin_headers: dict, reminder_id: str) -> None:
    httpx.delete(f"{API}/reminders/{reminder_id}", headers=admin_headers)


def _my_reminder_ids(headers: dict) -> set[str]:
    resp = httpx.get(
        f"{API}/reminders/me", params={"page_size": 100}, headers=headers
    )
    resp.raise_for_status()
    return {r["id"] for r in resp.json().get("data", [])}


def test_assigned_reminder_visible_to_assignee(
    carol_headers, bob_headers, alice_headers,
    carol, bob, alice,
    shared_category, shared_subcategory, shared_stage,
):
    """Carol creates reminder assigned to Bob; Bob sees it in /reminders/me."""
    doc = create_document(
        carol_headers,
        name="Carol Doc VIS-010",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=carol["id"],
    )
    reminder = _create_reminder(carol_headers, doc["id"], [carol["id"], bob["id"]])

    try:
        bob_ids = _my_reminder_ids(bob_headers)
        assert reminder["id"] in bob_ids, "Bob should see the reminder assigned to him"
    finally:
        _delete_reminder(alice_headers, reminder["id"])
        delete_document(carol_headers, doc["id"], my=True)


def test_unassigned_user_does_not_see_reminder(
    carol_headers, dave_headers, alice_headers,
    carol, bob, dave, alice,
    shared_category, shared_subcategory, shared_stage,
):
    """Reminder assigned to Carol and Bob is NOT visible to Dave."""
    doc = create_document(
        carol_headers,
        name="Carol Doc VIS-011",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=carol["id"],
    )
    reminder = _create_reminder(carol_headers, doc["id"], [carol["id"], bob["id"]])

    try:
        dave_ids = _my_reminder_ids(dave_headers)
        assert reminder["id"] not in dave_ids, "Dave should NOT see the reminder"
    finally:
        _delete_reminder(alice_headers, reminder["id"])
        delete_document(carol_headers, doc["id"], my=True)


def test_deleted_reminder_absent_from_assigned_users(
    carol_headers, bob_headers, dave_headers, alice_headers,
    carol, bob, dave, alice,
    shared_category, shared_subcategory, shared_stage,
):
    """After Carol deletes reminder, Bob and Dave no longer see it in /reminders/me."""
    doc = create_document(
        carol_headers,
        name="Carol Doc VIS-012",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=carol["id"],
    )
    reminder = _create_reminder(
        carol_headers, doc["id"], [carol["id"], bob["id"], dave["id"]]
    )
    reminder_id = reminder["id"]

    try:
        # Verify both users see it
        assert reminder_id in _my_reminder_ids(bob_headers)
        assert reminder_id in _my_reminder_ids(dave_headers)

        # Carol deletes it
        del_resp = httpx.delete(
            f"{API}/reminders/{reminder_id}/me", headers=carol_headers
        )
        assert del_resp.status_code == 200

        # Both users should no longer see it
        assert reminder_id not in _my_reminder_ids(bob_headers)
        assert reminder_id not in _my_reminder_ids(dave_headers)

        # Direct access returns 404
        for headers in (bob_headers, dave_headers):
            r = httpx.get(f"{API}/reminders/{reminder_id}/me", headers=headers)
            assert r.status_code == 404
    finally:
        delete_document(carol_headers, doc["id"], my=True)
