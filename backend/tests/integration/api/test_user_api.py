import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_user_success(client: AsyncClient, superuser_token: str):
    """Test POST /api/v1/users creates user."""
    response = await client.post(
        "/api/v1/users",
        json={
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "alice@example.com",
            "username": "alicejohnson",
            "password": "SecurePassword123",
            "is_active": True,
        },
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Alice"
    assert data["last_name"] == "Johnson"
    assert data["username"] == "alicejohnson"
    assert "password" not in data
    assert "id" in data


@pytest.mark.asyncio
async def test_get_users_success(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/users returns paginated users."""
    await client.post(
        "/api/v1/users",
        json={
            "first_name": "Bob",
            "last_name": "Smith",
            "username": "bobsmith",
            "password": "Password123",
            "is_active": True,
        },
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.get(
        "/api/v1/users?page=1&page_size=10",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "current_page" in data


@pytest.mark.asyncio
async def test_get_user_by_id_success(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/users/{id} returns user."""
    create_response = await client.post(
        "/api/v1/users",
        json={
            "first_name": "Charlie",
            "last_name": "Brown",
            "username": "charliebrown",
            "password": "Password123",
            "is_active": True,
        },
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.get(
        f"/api/v1/users/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "charliebrown"


@pytest.mark.asyncio
async def test_update_user_success(client: AsyncClient, superuser_token: str):
    """Test PUT /api/v1/users/{id} updates user."""
    create_response = await client.post(
        "/api/v1/users",
        json={
            "first_name": "David",
            "last_name": "Lee",
            "username": "davidlee",
            "password": "Password123",
            "is_active": True,
        },
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/users/{created['id']}",
        json={
            "first_name": "David",
            "last_name": "Lee-Smith",
            "email": "david@example.com",
            "username": "davidleesmith",
            "is_active": False,
        },
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["last_name"] == "Lee-Smith"
    assert data["username"] == "davidleesmith"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_delete_user_success(client: AsyncClient, superuser_token: str):
    """Test DELETE /api/v1/users/{id} deletes user."""
    create_response = await client.post(
        "/api/v1/users",
        json={
            "first_name": "Temp",
            "last_name": "User",
            "username": "tempuser123",
            "password": "Password123",
            "is_active": True,
        },
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.delete(
        f"/api/v1/users/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_duplicate_username_returns_400(
    client: AsyncClient, superuser_token: str
):
    """Test creating user with duplicate username returns 400."""
    user_data = {
        "first_name": "First",
        "last_name": "User",
        "username": "duplicateuser",
        "password": "Password123",
        "is_active": True,
    }

    response1 = await client.post(
        "/api/v1/users",
        json=user_data,
        headers={"X-Session-Key": superuser_token},
    )
    assert response1.status_code == 200

    user_data2 = {
        "first_name": "Second",
        "last_name": "User",
        "username": "duplicateuser",
        "password": "Password123",
        "is_active": True,
    }
    response2 = await client.post(
        "/api/v1/users",
        json=user_data2,
        headers={"X-Session-Key": superuser_token},
    )
    assert response2.status_code == 400


# Permission-based tests


@pytest.mark.asyncio
async def test_list_users_with_permission(
    client: AsyncClient, user_with_users_permissions: str
):
    """Test GET /api/v1/users succeeds with users.list permission."""
    response = await client.get(
        "/api/v1/users",
        headers={"X-Session-Key": user_with_users_permissions},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_users_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test GET /api/v1/users fails without users.list permission."""
    response = await client.get(
        "/api/v1/users",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_user_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test POST /api/v1/users fails without users.create permission."""
    # Create a role first
    role_response = await client.post(
        "/api/v1/roles",
        json={"name": "Test Role"},
        headers={"X-Session-Key": superuser_token},
    )
    role = role_response.json()

    response = await client.post(
        "/api/v1/users",
        json={
            "first_name": "Test",
            "last_name": "User",
            "username": "unauthorized_user",
            "password": "Password123",
            "role_id": role["id"],
        },
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_user_by_id_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test GET /api/v1/users/{id} fails without users.view permission."""
    role_response = await client.post(
        "/api/v1/roles",
        json={"name": "Test Role"},
        headers={"X-Session-Key": superuser_token},
    )
    role = role_response.json()

    create_response = await client.post(
        "/api/v1/users",
        json={
            "first_name": "Test",
            "last_name": "User",
            "username": "viewtest_user",
            "password": "Password123",
            "role_id": role["id"],
        },
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.get(
        f"/api/v1/users/{created['id']}",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_user_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test PUT /api/v1/users/{id} fails without users.update permission."""
    role_response = await client.post(
        "/api/v1/roles",
        json={"name": "Test Role"},
        headers={"X-Session-Key": superuser_token},
    )
    role = role_response.json()

    create_response = await client.post(
        "/api/v1/users",
        json={
            "first_name": "Test",
            "last_name": "User",
            "username": "updatetest_user",
            "password": "Password123",
            "role_id": role["id"],
        },
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/users/{created['id']}",
        json={
            "first_name": "Updated",
            "last_name": "User",
            "username": "updatetest_user",
            "role_id": role["id"],
        },
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_user_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test DELETE /api/v1/users/{id} fails without users.delete permission."""
    role_response = await client.post(
        "/api/v1/roles",
        json={"name": "Test Role"},
        headers={"X-Session-Key": superuser_token},
    )
    role = role_response.json()

    create_response = await client.post(
        "/api/v1/users",
        json={
            "first_name": "Test",
            "last_name": "User",
            "username": "deletetest_user",
            "password": "Password123",
            "role_id": role["id"],
        },
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.delete(
        f"/api/v1/users/{created['id']}",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403
