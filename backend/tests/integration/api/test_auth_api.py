import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, superuser_token: str):
    """Test POST /login with valid credentials."""
    await client.post(
        "/api/v1/users",
        json={
            "first_name": "Login",
            "last_name": "User",
            "username": "loginuser",
            "password": "LoginPassword123",
            "is_active": True,
        },
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.post(
        "/login",
        json={"username": "loginuser", "password": "LoginPassword123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "user" in data
    assert "expires_in" in data
    assert data["user"]["username"] == "loginuser"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_case_insensitive_username(
    client: AsyncClient, superuser_token: str
):
    """Test POST /login with uppercase username."""
    await client.post(
        "/api/v1/users",
        json={
            "first_name": "Case",
            "last_name": "Test",
            "username": "casetest",
            "password": "TestPassword123",
            "is_active": True,
        },
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.post(
        "/login",
        json={"username": "CASETEST", "password": "TestPassword123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["username"] == "casetest"


@pytest.mark.asyncio
async def test_login_invalid_username(client: AsyncClient):
    """Test POST /login with non-existent username."""
    response = await client.post(
        "/login",
        json={"username": "nonexistent", "password": "password"},
    )

    assert response.status_code == 401
    data = response.json()
    assert "Invalid username or password" in data["detail"]


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, superuser_token: str):
    """Test POST /login with wrong password."""
    await client.post(
        "/api/v1/users",
        json={
            "first_name": "Wrong",
            "last_name": "Pass",
            "username": "wrongpass",
            "password": "CorrectPassword123",
            "is_active": True,
        },
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.post(
        "/login",
        json={"username": "wrongpass", "password": "WrongPassword123"},
    )

    assert response.status_code == 401
    data = response.json()
    assert "Invalid username or password" in data["detail"]


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, superuser_token: str):
    """Test POST /login with inactive user."""
    await client.post(
        "/api/v1/users",
        json={
            "first_name": "Inactive",
            "last_name": "User",
            "username": "inactiveuser",
            "password": "Password123",
            "is_active": False,
        },
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.post(
        "/login",
        json={"username": "inactiveuser", "password": "Password123"},
    )

    assert response.status_code == 401
    data = response.json()
    assert "Inactive user" in data["detail"]


@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient, superuser_token: str):
    """Test POST /logout with valid session."""
    await client.post(
        "/api/v1/users",
        json={
            "first_name": "Logout",
            "last_name": "User",
            "username": "logoutuser",
            "password": "Password123",
            "is_active": True,
        },
        headers={"X-Session-Key": superuser_token},
    )

    login_response = await client.post(
        "/login",
        json={"username": "logoutuser", "password": "Password123"},
    )
    token = login_response.json()["token"]

    response = await client.post(
        "/logout",
        headers={"X-Session-Key": token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "invalidated" in data["detail"].lower()


@pytest.mark.asyncio
async def test_logout_invalid_session(client: AsyncClient):
    """Test POST /logout with invalid session token."""
    response = await client.post(
        "/logout",
        headers={"X-Session-Key": "invalid_token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_prevents_reuse(client: AsyncClient, superuser_token: str):
    """Test that logged out session cannot be reused."""
    await client.post(
        "/api/v1/users",
        json={
            "first_name": "Reuse",
            "last_name": "Test",
            "username": "reusetest",
            "password": "Password123",
            "is_active": True,
        },
        headers={"X-Session-Key": superuser_token},
    )

    login_response = await client.post(
        "/login",
        json={"username": "reusetest", "password": "Password123"},
    )
    token = login_response.json()["token"]

    await client.post(
        "/logout",
        headers={"X-Session-Key": token},
    )

    response = await client.get(
        "/api/v1/users?page=1&page_size=10",
        headers={"X-Session-Key": token},
    )

    assert response.status_code == 401
