import httpx

from tests.api.conftest import API, create_document, delete_document


def _create_reminder(headers: dict, doc_id: str, assign_user_ids: list[str]) -> dict:
    resp = httpx.post(
        f"{API}/documents/{doc_id}/reminders/me",
        json={
            "date": "2030-01-01",
            "time": "09:00:00",
            "subject": "E2E Reminder",
            "message": "E2E reminder message",
            "assign_user": assign_user_ids,
        },
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def _delete_reminder(headers: dict, reminder_id: str) -> None:
    httpx.delete(f"{API}/reminders/{reminder_id}/me", headers=headers)


def test_carol_global_reminder_endpoints_return_403(carol_headers):
    """Carol has only my-scope reminder permissions; global endpoints must return 403."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    endpoints = [
        ("GET",    f"{API}/reminders"),
        ("GET",    f"{API}/reminders/{fake_id}"),
        ("DELETE", f"{API}/reminders/{fake_id}"),
        ("PUT",    f"{API}/reminders/{fake_id}"),
    ]
    for method, url in endpoints:
        resp = httpx.request(method, url, headers=carol_headers)
        assert resp.status_code == 403, (
            f"{method} {url} returned {resp.status_code}, expected 403"
        )


def test_dave_cannot_update_or_delete_reminder(
    alice_headers, dave_headers, alice, dave,
    shared_category, shared_subcategory, shared_stage,
):
    """Dave has only view/list permissions for reminders; update and delete must return 403."""
    doc = create_document(
        alice_headers,
        name="Alice Doc PERM-021",
        category_id=shared_category["id"],
        subcategory_id=shared_subcategory["id"],
        stage_id=shared_stage["id"],
        assigned_to=alice["id"],
    )
    reminder = _create_reminder(alice_headers, doc["id"], [alice["id"], dave["id"]])

    try:
        delete_resp = httpx.delete(
            f"{API}/reminders/{reminder['id']}/me", headers=dave_headers
        )
        assert delete_resp.status_code == 403

        update_resp = httpx.put(
            f"{API}/reminders/{reminder['id']}/me",
            json={
                "date": "2030-02-01",
                "time": "10:00:00",
                "subject": "Hacked Subject",
                "message": "Hacked message",
                "assign_user": [alice["id"]],
            },
            headers=dave_headers,
        )
        assert update_resp.status_code == 403
    finally:
        _delete_reminder(alice_headers, reminder["id"])
        delete_document(alice_headers, doc["id"])
