import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_role_success(client: AsyncClient, superuser_token: str):
    """Test POST /api/v1/roles creates role."""
    response = await client.post(
        "/api/v1/roles",
        json={
            "name": "Project Manager",
            "description": "Manages projects",
            "is_active": True,
        },
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Project Manager"
    assert data["description"] == "Manages projects"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_get_roles_success(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/roles returns paginated roles."""
    await client.post(
        "/api/v1/roles",
        json={"name": "Test Role", "description": "Test", "is_active": True},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.get(
        "/api/v1/roles?page=1&page_size=10",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_get_role_by_id_success(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/roles/{id} returns role."""
    create_response = await client.post(
        "/api/v1/roles",
        json={"name": "Viewer Role", "description": "Can view", "is_active": True},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.get(
        f"/api/v1/roles/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Viewer Role"


@pytest.mark.asyncio
async def test_update_role_success(client: AsyncClient, superuser_token: str):
    """Test PUT /api/v1/roles/{id} updates role."""
    create_response = await client.post(
        "/api/v1/roles",
        json={"name": "Editor Role", "description": "Can edit", "is_active": True},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/roles/{created['id']}",
        json={
            "name": "Senior Editor",
            "description": "Senior editor role",
            "permissions": [],
        },
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Senior Editor"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_delete_role_success(client: AsyncClient, superuser_token: str):
    """Test DELETE /api/v1/roles/{id} deletes role."""
    create_response = await client.post(
        "/api/v1/roles",
        json={"name": "Temp Role", "description": "Temporary", "is_active": True},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.delete(
        f"/api/v1/roles/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_role_status_deactivate_success(
    client: AsyncClient, superuser_token: str
):
    """Test PATCH /api/v1/roles/{id}/status deactivates role."""
    create_response = await client.post(
        "/api/v1/roles",
        json={"name": "Active Role", "description": "Active", "is_active": True},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.patch(
        f"/api/v1/roles/{created['id']}/status",
        json={"is_active": False},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_update_role_status_activate_success(
    client: AsyncClient, superuser_token: str
):
    """Test PATCH /api/v1/roles/{id}/status activates role."""
    create_response = await client.post(
        "/api/v1/roles",
        json={"name": "Inactive Role", "description": "Inactive", "is_active": False},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.patch(
        f"/api/v1/roles/{created['id']}/status",
        json={"is_active": True},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_update_role_status_not_found(client: AsyncClient, superuser_token: str):
    """Test PATCH /api/v1/roles/{id}/status returns 404 for non-existent role."""
    from uuid import uuid4

    response = await client.patch(
        f"/api/v1/roles/{uuid4()}/status",
        json={"is_active": False},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


# Permission-based tests


@pytest.mark.asyncio
async def test_list_roles_with_permission(
    client: AsyncClient, user_with_roles_permissions: str
):
    """Test GET /api/v1/roles succeeds with roles.list permission."""
    response = await client.get(
        "/api/v1/roles",
        headers={"X-Session-Key": user_with_roles_permissions},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_roles_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test GET /api/v1/roles fails without roles.list permission."""
    response = await client.get(
        "/api/v1/roles",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_role_with_permission(
    client: AsyncClient, user_with_roles_permissions: str
):
    """Test POST /api/v1/roles succeeds with roles.create permission."""
    response = await client.post(
        "/api/v1/roles",
        json={"name": "Authorized Role"},
        headers={"X-Session-Key": user_with_roles_permissions},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_role_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test POST /api/v1/roles fails without roles.create permission."""
    response = await client.post(
        "/api/v1/roles",
        json={"name": "Unauthorized Role"},
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_role_by_id_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test GET /api/v1/roles/{id} fails without roles.view permission."""
    create_response = await client.post(
        "/api/v1/roles",
        json={"name": "View Test Role"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.get(
        f"/api/v1/roles/{created['id']}",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_role_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test PUT /api/v1/roles/{id} fails without roles.update permission."""
    create_response = await client.post(
        "/api/v1/roles",
        json={"name": "Before Role"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/roles/{created['id']}",
        json={"name": "After Role"},
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_role_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test DELETE /api/v1/roles/{id} fails without roles.delete permission."""
    create_response = await client.post(
        "/api/v1/roles",
        json={"name": "To Delete Role"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.delete(
        f"/api/v1/roles/{created['id']}",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_assign_permissions_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test POST /api/v1/roles/{id}/permissions fails without roles.assign_permissions."""
    create_response = await client.post(
        "/api/v1/roles",
        json={"name": "Test Role"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    perms_response = await client.get(
        "/api/v1/permissions",
        headers={"X-Session-Key": superuser_token},
    )
    perms = perms_response.json()

    response = await client.post(
        f"/api/v1/roles/{created['id']}/permissions",
        json={"permission_ids": [perms[0]["id"]]},
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403
