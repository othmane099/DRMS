import os
import sys

import pytest
import pytest_asyncio
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from auth.sessions.service import SessionServiceImpl
from auth.users.schemas import UserCreate
from auth.users.service import UserServiceImpl
from schemas import Error, Message
from unit_of_work.fake_uow import FakeUnitOfWork


@pytest.fixture
def uow():
    """Provide a fake unit of work."""
    return FakeUnitOfWork()


@pytest.fixture
def session_service(uow):
    """Provide a session service with fake UoW."""
    return SessionServiceImpl(unit_of_work=uow)


@pytest.fixture
def user_service(uow):
    """Provide a user service with fake UoW."""
    return UserServiceImpl(unit_of_work=uow)


@pytest_asyncio.fixture
async def test_user(user_service):
    """Create a test user for session tests."""
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


@pytest.mark.asyncio
async def test_create_session_success(session_service, test_user, uow):
    """Test creating a new session successfully."""
    result = await session_service.create_session(test_user.id, uow)

    assert not isinstance(result, Error)
    assert result.user_id == test_user.id
    assert result.is_active is True
    assert len(result.token) > 0
    assert result.expired_at is not None


@pytest.mark.asyncio
async def test_get_active_session_by_token_success(session_service, test_user, uow):
    """Test retrieving an active session by token."""
    created_session = await session_service.create_session(test_user.id, uow)
    assert not isinstance(created_session, Error)

    result = await session_service.get_active_session(created_session.token)

    assert not isinstance(result, Error)
    assert result.id == created_session.id
    assert result.token == created_session.token
    assert result.is_active is True


@pytest.mark.asyncio
async def test_get_active_session_invalid_token(session_service):
    """Test retrieving a session with invalid token returns error."""
    result = await session_service.get_active_session("invalid-token-12345")

    assert isinstance(result, Error)
    assert result.code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_revoke_session_success(session_service, test_user, uow):
    """Test revoking a session successfully."""
    created_session = await session_service.create_session(test_user.id, uow)
    assert not isinstance(created_session, Error)

    result = await session_service.invalidate_session(created_session.token)

    assert isinstance(result, Message)
    assert "invalidate" in result.detail.lower() or "revoked" in result.detail.lower()

    get_result = await session_service.get_active_session(created_session.token)
    assert isinstance(get_result, Error)


@pytest.mark.asyncio
async def test_revoke_session_invalid_token(session_service):
    """Test revoking a session with invalid token returns error."""
    result = await session_service.invalidate_session("invalid-token-12345")

    assert isinstance(result, Error)
    assert result.code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_session_token_uniqueness(session_service, test_user, uow):
    """Test that each session gets a unique token."""
    session1 = await session_service.create_session(test_user.id, uow)
    session2 = await session_service.create_session(test_user.id, uow)

    assert not isinstance(session1, Error)
    assert not isinstance(session2, Error)
    assert session1.token != session2.token
