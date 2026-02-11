import secrets
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
import pytz
from httpx import AsyncClient
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from sqlalchemy import select

from auth.models import LoggedHistory, LoggedHistoryType, Permission, Role, User
from auth.models import Session as SessionModel
from db import default_session_factory


@pytest_asyncio.fixture
async def user_with_logged_histories_permissions(client: AsyncClient):  # noqa: ARG001
    """Create a user with logged_histories.view permission and return auth token."""
    async with default_session_factory() as session:
        stmt = select(Permission).where(Permission.code == "logged_histories.view")
        result = await session.execute(stmt)
        permissions = list(result.scalars().all())

        role = Role(name="Logged Histories Viewer", is_active=True)
        role.permissions = permissions
        session.add(role)
        await session.flush()

        hashed_password = pbkdf2_sha256.hash("TestPassword123")
        user = User(
            first_name="Logged",
            last_name="Viewer",
            username="logged_histories_viewer_test",
            password=hashed_password,
            is_active=True,
            is_superuser=False,
            role_id=role.id,
        )
        session.add(user)
        await session.flush()

        token = secrets.token_urlsafe(32)
        user_session = SessionModel(
            user_id=user.id,
            token=token,
            expired_at=datetime.now(pytz.utc) + timedelta(hours=24),
            is_active=True,
        )
        session.add(user_session)
        await session.commit()

        return token


async def _seed_logged_histories(count: int = 3) -> list[LoggedHistory]:
    """Seed logged history records directly into the database."""
    records = []
    async with default_session_factory() as session:
        for i in range(count):
            lh = LoggedHistory(
                ip=f"192.168.1.{i + 1}",
                date=datetime.now(pytz.utc) - timedelta(hours=i),
                details={"info": f"entry {i}"},
                type=LoggedHistoryType.LOGIN
                if i % 2 == 0
                else LoggedHistoryType.FAILED_LOGIN,
            )
            session.add(lh)
        await session.flush()
        for obj in session.new:
            records.append(obj)
        await session.commit()
    return records


@pytest.mark.asyncio
async def test_get_logged_histories_returns_empty_when_no_data(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/logged-history returns empty data when nothing is seeded."""
    response = await client.get(
        "/api/v1/logged-history",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["total_rows"] == 0
    assert data["current_page"] == 1


@pytest.mark.asyncio
async def test_get_logged_histories_returns_seeded_data(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/logged-history returns seeded records."""
    await _seed_logged_histories(3)

    response = await client.get(
        "/api/v1/logged-history",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 3
    assert len(data["data"]) == 3


@pytest.mark.asyncio
async def test_get_logged_histories_response_shape(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/logged-history response has correct shape."""
    await _seed_logged_histories(1)

    response = await client.get(
        "/api/v1/logged-history",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "current_page" in data
    assert "total_pages" in data
    assert "total_rows" in data
    assert "page_size" in data
    assert "has_next" in data
    assert "has_previous" in data

    entry = data["data"][0]
    assert "id" in entry
    assert "user_id" in entry
    assert "ip" in entry
    assert "date" in entry
    assert "details" in entry
    assert "type" in entry


@pytest.mark.asyncio
async def test_get_logged_histories_with_permission(
    client: AsyncClient, user_with_logged_histories_permissions: str
):
    """Test GET /api/v1/logged-history succeeds with logged_histories.view permission."""
    response = await client.get(
        "/api/v1/logged-history",
        headers={"X-Session-Key": user_with_logged_histories_permissions},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_logged_histories_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test GET /api/v1/logged-history fails without logged_histories.view permission."""
    response = await client.get(
        "/api/v1/logged-history",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_logged_histories_pagination(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/logged-history pagination params are respected."""
    await _seed_logged_histories(5)

    response = await client.get(
        "/api/v1/logged-history",
        params={"page": 1, "page_size": 2},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["current_page"] == 1
    assert data["page_size"] == 2
    assert len(data["data"]) == 2
    assert data["total_rows"] == 5
    assert data["total_pages"] == 3
    assert data["has_next"] is True
    assert data["has_previous"] is False


@pytest.mark.asyncio
async def test_get_logged_histories_second_page(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/logged-history second page has correct state."""
    await _seed_logged_histories(5)

    response = await client.get(
        "/api/v1/logged-history",
        params={"page": 2, "page_size": 2},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["current_page"] == 2
    assert data["has_next"] is True
    assert data["has_previous"] is True


@pytest.mark.asyncio
async def test_get_logged_histories_filter_by_type(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/logged-history filters by type."""
    await _seed_logged_histories(4)

    response = await client.get(
        "/api/v1/logged-history",
        params={"type": "login"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert all(entry["type"] == "login" for entry in data["data"])


@pytest.mark.asyncio
async def test_get_logged_histories_filter_by_user_id(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/logged-history filters by user_id."""
    async with default_session_factory() as session:
        hashed_password = pbkdf2_sha256.hash("TestPassword123")
        user = User(
            first_name="Filter",
            last_name="Target",
            username="filter_target_test",
            password=hashed_password,
            is_active=True,
        )
        session.add(user)
        await session.flush()
        user_id = user.id

        lh_with_user = LoggedHistory(
            user_id=user_id,
            ip="10.0.0.1",
            date=datetime.now(pytz.utc),
            details={"action": "login"},
            type=LoggedHistoryType.LOGIN,
        )
        lh_anonymous = LoggedHistory(
            ip="10.0.0.2",
            date=datetime.now(pytz.utc),
            details={"action": "failed"},
            type=LoggedHistoryType.FAILED_LOGIN,
        )
        session.add(lh_with_user)
        session.add(lh_anonymous)
        await session.commit()

    response = await client.get(
        "/api/v1/logged-history",
        params={"user_id": str(user_id)},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 1
    assert data["data"][0]["user_id"] == str(user_id)


@pytest.mark.asyncio
async def test_get_logged_histories_filter_by_date_range(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/logged-history filters by date_from and date_to."""
    now = datetime.now(pytz.utc)
    async with default_session_factory() as session:
        old = LoggedHistory(
            ip="1.1.1.1",
            date=now - timedelta(days=5),
            details={},
            type=LoggedHistoryType.LOGIN,
        )
        recent = LoggedHistory(
            ip="2.2.2.2",
            date=now - timedelta(hours=1),
            details={},
            type=LoggedHistoryType.LOGIN,
        )
        session.add(old)
        session.add(recent)
        await session.commit()

    date_from = (now - timedelta(days=1)).isoformat()
    response = await client.get(
        "/api/v1/logged-history",
        params={"date_from": date_from},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 1
    assert data["data"][0]["ip"] == "2.2.2.2"


@pytest.mark.asyncio
async def test_get_logged_histories_filter_by_search(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/logged-history filters by search in details."""
    async with default_session_factory() as session:
        lh1 = LoggedHistory(
            ip="1.1.1.1",
            date=datetime.now(pytz.utc),
            details={"message": "browser chrome"},
            type=LoggedHistoryType.LOGIN,
        )
        lh2 = LoggedHistory(
            ip="2.2.2.2",
            date=datetime.now(pytz.utc),
            details={"message": "browser firefox"},
            type=LoggedHistoryType.LOGIN,
        )
        session.add(lh1)
        session.add(lh2)
        await session.commit()

    response = await client.get(
        "/api/v1/logged-history",
        params={"search": "chrome"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 1
    assert data["data"][0]["ip"] == "1.1.1.1"


@pytest.mark.asyncio
async def test_get_logged_histories_includes_user_name(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/logged-history includes user_name when user exists."""
    async with default_session_factory() as session:
        hashed_password = pbkdf2_sha256.hash("TestPassword123")
        user = User(
            first_name="Jane",
            last_name="Doe",
            username="jane_doe_lh_test",
            password=hashed_password,
            is_active=True,
        )
        session.add(user)
        await session.flush()

        lh = LoggedHistory(
            user_id=user.id,
            ip="9.9.9.9",
            date=datetime.now(pytz.utc),
            details={},
            type=LoggedHistoryType.LOGIN,
        )
        session.add(lh)
        await session.commit()

    response = await client.get(
        "/api/v1/logged-history",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 1
    entry = data["data"][0]
    assert entry["user_name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_get_logged_histories_unauthenticated(client: AsyncClient):
    """Test GET /api/v1/logged-history returns 422 when session key header is absent."""
    response = await client.get("/api/v1/logged-history")

    assert response.status_code == 422
