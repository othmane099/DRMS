import os
import secrets
import sys
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
import pytz
from sqlalchemy import select
from starlette import status

sys.path.insert(0, f"{os.getcwd()}/src")

from auth.models import Session  # noqa: E402
from auth.sessions.service import SessionServiceImpl  # noqa: E402
from auth.users.schemas import UserCreate  # noqa: E402
from auth.users.service import UserServiceImpl  # noqa: E402
from db import default_session_factory  # noqa: E402
from schemas import Error, Message  # noqa: E402
from unit_of_work.uow import UnitOfWorkImpl  # noqa: E402


@pytest.fixture
def user_service():
    uow = UnitOfWorkImpl(session_factory=default_session_factory)
    return UserServiceImpl(unit_of_work=uow)


@pytest.fixture
def session_service():
    uow = UnitOfWorkImpl(session_factory=default_session_factory)
    return SessionServiceImpl(unit_of_work=uow)


@pytest_asyncio.fixture
async def test_user(user_service):
    user_data = UserCreate(
        first_name="Session",
        last_name="Tester",
        username="sessiontester",
        password="SecurePass123",
        is_active=True,
    )
    user = await user_service.create_user(user_data)
    assert not isinstance(user, Error)
    return user


@pytest_asyncio.fixture
async def active_session(test_user) -> Session:
    async with UnitOfWorkImpl(session_factory=default_session_factory) as uow:
        session = await uow.session_repository.create_session(
            user_id=test_user.id,
            session_token=secrets.token_urlsafe(32),
            expired_at=datetime.now(pytz.utc) + timedelta(hours=24),
        )
        await uow.commit()
        return session


@pytest.mark.asyncio
async def test_get_active_session_persisted_in_database(
    session_service, active_session
):
    """Test that get_active_session retrieves a persisted session from the database."""
    result = await session_service.get_active_session(active_session.token)

    assert not isinstance(result, Error)
    assert result.id == active_session.id
    assert result.token == active_session.token
    assert result.is_active is True

    async with default_session_factory() as db:
        db_result = await db.execute(
            select(Session).where(Session.id == active_session.id)
        )
        db_session = db_result.scalar_one_or_none()

        assert db_session is not None
        assert db_session.is_active is True
        assert db_session.deleted_at is None


@pytest.mark.asyncio
async def test_get_active_session_invalid_token(session_service):
    """Test that get_active_session returns an error for a non-existent token."""
    result = await session_service.get_active_session("nonexistent-token-xyz")

    assert isinstance(result, Error)
    assert result.code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_invalidate_session_commits_to_database(session_service, active_session):
    """Test that invalidate_session sets is_active=False in the database."""
    result = await session_service.invalidate_session(active_session.token)

    assert isinstance(result, Message)

    async with default_session_factory() as db:
        db_result = await db.execute(
            select(Session).where(Session.id == active_session.id)
        )
        db_session = db_result.scalar_one_or_none()

        assert db_session is not None
        assert db_session.is_active is False


@pytest.mark.asyncio
async def test_invalidate_session_invalid_token(session_service):
    """Test that invalidate_session returns an error for a non-existent token."""
    result = await session_service.invalidate_session("nonexistent-token-xyz")

    assert isinstance(result, Error)
    assert result.code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_invalidate_session_already_invalidated(session_service, active_session):
    """Test that invalidating an already-invalidated session returns an error."""
    await session_service.invalidate_session(active_session.token)

    result = await session_service.invalidate_session(active_session.token)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_401_UNAUTHORIZED
