import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, f"{os.getcwd()}/src")

from fastapi import HTTPException  # noqa: E402

from auth.api import login, logout  # noqa: E402
from auth.fakes import FakeAuthService  # noqa: E402
from auth.schemas import LoginRequest  # noqa: E402
from auth.sessions.fakes import FakeSessionService  # noqa: E402
from auth.users.schemas import UserCreate  # noqa: E402


@pytest.fixture
def auth_service():
    """Provide FakeAuthService for testing."""
    return FakeAuthService()


@pytest.fixture
def session_service():
    """Provide FakeSessionService."""
    return FakeSessionService()


@pytest.fixture
def mock_request():
    """Provide a mock Request object with client IP."""
    request = MagicMock()
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
async def setup_test_user(auth_service):
    """Create a test user for authentication tests."""
    user_data = UserCreate(
        first_name="Test",
        last_name="User",
        username="testuser",
        password="TestPassword123",
        is_active=True,
    )
    await auth_service._user_service.create_user(user_data)


@pytest.mark.asyncio
async def test_login_success(auth_service, setup_test_user, mock_request):
    """Test POST /login endpoint with valid credentials."""
    body = LoginRequest(username="testuser", password="TestPassword123")

    result = await login(body=body, request=mock_request, auth_service=auth_service)

    assert result.token is not None
    assert result.user.username == "testuser"
    assert result.expires_in > 0


@pytest.mark.asyncio
async def test_login_invalid_credentials(auth_service, mock_request):
    """Test POST /login endpoint with invalid credentials."""
    body = LoginRequest(username="nonexistent", password="password")

    with pytest.raises(HTTPException) as exc_info:
        await login(body=body, request=mock_request, auth_service=auth_service)

    assert exc_info.value.status_code == 401
    assert "Invalid username or password" in exc_info.value.detail


@pytest.mark.asyncio
async def test_login_inactive_user(auth_service, mock_request):
    """Test POST /login endpoint with inactive user."""
    user_data = UserCreate(
        first_name="Inactive",
        last_name="User",
        username="inactiveuser",
        password="TestPassword123",
        is_active=False,
    )
    await auth_service._user_service.create_user(user_data)

    body = LoginRequest(username="inactiveuser", password="TestPassword123")

    with pytest.raises(HTTPException) as exc_info:
        await login(body=body, request=mock_request, auth_service=auth_service)

    assert exc_info.value.status_code == 401
    assert "Inactive user" in exc_info.value.detail


@pytest.mark.asyncio
async def test_logout_success(auth_service, setup_test_user, mock_request):
    """Test POST /logout endpoint with valid session."""
    body = LoginRequest(username="testuser", password="TestPassword123")
    login_result = await login(
        body=body, request=mock_request, auth_service=auth_service
    )
    token = login_result.token

    result = await logout(
        x_session_key=token, session_service=auth_service._session_service
    )

    assert result.detail == "Sessions invalidated successfully"


@pytest.mark.asyncio
async def test_logout_invalid_session(session_service):
    """Test POST /logout endpoint with invalid session token."""
    with pytest.raises(HTTPException) as exc_info:
        await logout(x_session_key="invalid_token", session_service=session_service)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_logout_already_invalidated(auth_service, setup_test_user, mock_request):
    """Test POST /logout endpoint with already invalidated session."""
    body = LoginRequest(username="testuser", password="TestPassword123")
    login_result = await login(
        body=body, request=mock_request, auth_service=auth_service
    )
    token = login_result.token

    await logout(x_session_key=token, session_service=auth_service._session_service)

    with pytest.raises(HTTPException) as exc_info:
        await logout(x_session_key=token, session_service=auth_service._session_service)

    assert exc_info.value.status_code == 401
