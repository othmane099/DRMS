import uuid
from typing import Generator

import httpx
import pytest

API = "http://localhost:8000/api/v1"
BASE = "http://localhost:8000"

# ── Tiny test file attached to every document create call ─────────────────────
DUMMY_FILE = ("test.txt", b"dummy content for e2e tests", "text/plain")

# ── User permission profiles ──────────────────────────────────────────────────

MANAGER_PERMS = [
    "documents.list", "documents.view", "documents.create", "documents.update",
    "documents.delete", "documents.archive", "documents.download", "documents.share",
    "documents.view_version", "documents.create_version", "documents.download_version",
    "documents.preview_version", "documents.history",
    "documents.list_my", "documents.view_my", "documents.create_my", "documents.update_my",
    "documents.delete_my", "documents.archive_my", "documents.download_my", "documents.share_my",
    "documents.view_version_my", "documents.create_version_my", "documents.history_my",
    "reminders.list", "reminders.view", "reminders.create", "reminders.update", "reminders.delete",
    "reminders.list_my", "reminders.view_my", "reminders.create_my", "reminders.update_my",
    "reminders.delete_my",
    "comments.list", "comments.create", "comments.list_my", "comments.create_my",
]

CLIENT_PERMS = [
    "documents.list", "documents.view", "documents.download", "documents.share_my",
    "documents.list_my", "documents.view_my", "documents.download_my",
    "reminders.list", "reminders.view", "reminders.list_my", "reminders.view_my",
]

EMPLOYEE_PERMS = [
    "documents.create_my", "documents.list_my", "documents.view_my", "documents.update_my",
    "documents.delete_my", "documents.archive_my", "documents.download_my", "documents.share_my",
    "documents.create_version_my",
    "reminders.create_my", "reminders.list_my", "reminders.view_my",
    "reminders.update_my", "reminders.delete_my",
]

GUEST_PERMS = [
    "documents.list_my", "documents.view_my", "documents.download_my",
    "reminders.list_my", "reminders.view_my",
]

EMPTY_PERMS: list[str] = []


# ── Helper ────────────────────────────────────────────────────────────────────

def _token(username: str, password: str) -> str:
    resp = httpx.post(f"{BASE}/login", json={"username": username, "password": password})
    resp.raise_for_status()
    return resp.json()["token"]


def _headers(token: str) -> dict[str, str]:
    return {"X-Session-Key": token}


def _create_user(
    admin_headers: dict[str, str],
    *,
    username: str,
    password: str,
    perms: list[str],
) -> dict:
    suffix = uuid.uuid4().hex[:6]
    resp = httpx.post(
        f"{API}/users",
        json={
            "first_name": username.capitalize(),
            "last_name": "E2E",
            "username": f"{username}_{suffix}",
            "password": password,
            "is_active": True,
            "role_id": None,
        },
        headers=admin_headers,
    )
    resp.raise_for_status()
    user = resp.json()

    if perms:
        perm_resp = httpx.patch(
            f"{API}/users/{user['id']}/permissions",
            json={"permissions": perms},
            headers=admin_headers,
        )
        perm_resp.raise_for_status()

    return user


def _delete_user(admin_headers: dict[str, str], user_id: str) -> None:
    httpx.delete(f"{API}/users/{user_id}", headers=admin_headers)


# ── Session-scoped token / client fixtures ────────────────────────────────────

@pytest.fixture(scope="session")
def superuser_token() -> str:
    return _token("superuser", "superuser123")


@pytest.fixture(scope="session")
def admin_headers(superuser_token: str) -> dict[str, str]:
    return _headers(superuser_token)


# ── Shared resources (category / subcategory / stage) ────────────────────────

@pytest.fixture(scope="session")
def shared_stage(admin_headers: dict[str, str]) -> Generator[dict, None, None]:
    resp = httpx.post(
        f"{API}/stages",
        json={"title": f"e2e-stage-{uuid.uuid4().hex[:6]}", "color": "#123456"},
        headers=admin_headers,
    )
    resp.raise_for_status()
    stage = resp.json()
    yield stage
    httpx.delete(f"{API}/stages/{stage['id']}", headers=admin_headers)


@pytest.fixture(scope="session")
def shared_category(admin_headers: dict[str, str]) -> Generator[dict, None, None]:
    resp = httpx.post(
        f"{API}/categories",
        json={"title": f"e2e-cat-{uuid.uuid4().hex[:6]}"},
        headers=admin_headers,
    )
    resp.raise_for_status()
    cat = resp.json()
    yield cat
    httpx.delete(f"{API}/categories/{cat['id']}", headers=admin_headers)


@pytest.fixture(scope="session")
def shared_subcategory(
    admin_headers: dict[str, str],
    shared_category: dict,
) -> Generator[dict, None, None]:
    resp = httpx.post(
        f"{API}/subcategories",
        json={
            "title": f"e2e-subcat-{uuid.uuid4().hex[:6]}",
            "category_id": shared_category["id"],
        },
        headers=admin_headers,
    )
    resp.raise_for_status()
    sub = resp.json()
    yield sub
    httpx.delete(f"{API}/subcategories/{sub['id']}", headers=admin_headers)


# ── Test user fixtures ────────────────────────────────────────────────────────

def _user_fixture(username: str, password: str, perms: list[str]):
    @pytest.fixture(scope="session")
    def fixture(admin_headers: dict[str, str]) -> Generator[dict, None, None]:
        user = _create_user(admin_headers, username=username, password=password, perms=perms)
        yield user
        _delete_user(admin_headers, user["id"])
    return fixture


alice = _user_fixture("alice", "Alice123!", MANAGER_PERMS)
bob = _user_fixture("bob", "Bob123!", CLIENT_PERMS)
carol = _user_fixture("carol", "Carol123!", EMPLOYEE_PERMS)
dave = _user_fixture("dave", "Dave123!", GUEST_PERMS)
eve = _user_fixture("eve", "Eve123!", EMPTY_PERMS)


@pytest.fixture(scope="session")
def alice_headers(alice: dict) -> dict[str, str]:
    tok = _token(alice["username"], "Alice123!")
    return _headers(tok)


@pytest.fixture(scope="session")
def bob_headers(bob: dict) -> dict[str, str]:
    tok = _token(bob["username"], "Bob123!")
    return _headers(tok)


@pytest.fixture(scope="session")
def carol_headers(carol: dict) -> dict[str, str]:
    tok = _token(carol["username"], "Carol123!")
    return _headers(tok)


@pytest.fixture(scope="session")
def dave_headers(dave: dict) -> dict[str, str]:
    tok = _token(dave["username"], "Dave123!")
    return _headers(tok)


@pytest.fixture(scope="session")
def eve_headers(eve: dict) -> dict[str, str]:
    tok = _token(eve["username"], "Eve123!")
    return _headers(tok)


# ── Document creation helper ──────────────────────────────────────────────────

def create_document(
    headers: dict[str, str],
    *,
    name: str,
    category_id: str,
    subcategory_id: str,
    stage_id: str,
    assigned_to: str,
) -> dict:
    # Append a short UUID suffix so names are globally unique across repeated runs.
    unique_name = f"{name}-{uuid.uuid4().hex[:6]}"
    # POST /documents is the only create endpoint; documents.create_my also grants access to it
    resp = httpx.post(
        f"{API}/documents",
        data={
            "name": unique_name,
            "category_id": category_id,
            "subcategory_id": subcategory_id,
            "stage_id": stage_id,
            "assigned_to": assigned_to,
        },
        files={"document": DUMMY_FILE},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def delete_document(headers: dict[str, str], doc_id: str, my: bool = False) -> None:
    url = f"{API}/documents/{doc_id}/me" if my else f"{API}/documents/{doc_id}"
    httpx.delete(url, headers=headers)