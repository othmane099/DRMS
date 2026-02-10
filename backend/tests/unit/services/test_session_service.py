import os
import sys

import pytest
import pytest_asyncio
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from auth.models import Session
from auth.sessions.service import SessionServiceImpl
from auth.users.schemas import UserCreate
from auth.users.service import UserServiceImpl
from schemas import Error, Message
from unit_of_work.fake_uow import FakeUnitOfWork


@pytest.fixture
def uow():
    return FakeUnitOfWork()


@pytest.fixture
def session_service(uow):
    return SessionServiceImpl(unit_of_work=uow)


@pytest.fixture
def user_service(uow):
    return UserServiceImpl(unit_of_work=uow)


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
async def active_session(test_user, uow) -> Session:
    import secrets
    from datetime import datetime, timedelta

    import pytz

    return await uow.session_repository.create_session(
        user_id=test_user.id,
        session_token=secrets.token_urlsafe(32),
        expired_at=datetime.now(pytz.utc) + timedelta(hours=24),
    )


@pytest.mark.asyncio
async def test_get_active_session_by_token_success(session_service, active_session):
    """Test retrieving an active session by token."""
    result = await session_service.get_active_session(active_session.token)

    assert not isinstance(result, Error)
    assert result.id == active_session.id
    assert result.token == active_session.token
    assert result.is_active is True


@pytest.mark.asyncio
async def test_get_active_session_invalid_token(session_service):
    """Test retrieving a session with invalid token returns error."""
    result = await session_service.get_active_session("invalid-token-12345")

    assert isinstance(result, Error)
    assert result.code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_revoke_session_success(session_service, active_session):
    """Test revoking a session successfully."""
    result = await session_service.invalidate_session(active_session.token)

    assert isinstance(result, Message)
    assert "invalidate" in result.detail.lower() or "revoked" in result.detail.lower()

    get_result = await session_service.get_active_session(active_session.token)
    assert isinstance(get_result, Error)


@pytest.mark.asyncio
async def test_revoke_session_invalid_token(session_service):
    """Test revoking a session with invalid token returns error."""
    result = await session_service.invalidate_session("invalid-token-12345")

    assert isinstance(result, Error)
    assert result.code == status.HTTP_401_UNAUTHORIZED
