from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from auth.models import Permission
from db import default_session_factory


@pytest.mark.asyncio
async def test_create_role_success(client: AsyncClient, superuser_token: str):
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
    await client.post(
        "/api/v1/roles",
        json={"name": "Test Role", "description": "Test", "is_active": True},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.get(
        "/api/v1/roles",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_get_role_by_id_success(client: AsyncClient, superuser_token: str):
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
    assert response.json()["name"] == "Viewer Role"


@pytest.mark.asyncio
async def test_update_role_success(client: AsyncClient, superuser_token: str):
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
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_update_role_status_activate_success(
    client: AsyncClient, superuser_token: str
):
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
    assert response.json()["is_active"] is True


@pytest.mark.asyncio
async def test_update_role_status_not_found(client: AsyncClient, superuser_token: str):
    response = await client.patch(
        f"/api/v1/roles/{uuid4()}/status",
        json={"is_active": False},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_assign_permissions_success(client: AsyncClient, superuser_token: str):
    create_response = await client.post(
        "/api/v1/roles",
        json={
            "name": "Managed Role",
            "description": "Role with perms",
            "is_active": True,
        },
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    async with default_session_factory() as db:
        perm_ids = (
            (
                await db.execute(
                    select(Permission.id).where(
                        Permission.code.in_(["roles.list", "roles.view"])
                    )
                )
            )
            .scalars()
            .all()
        )

    response = await client.post(
        f"/api/v1/roles/{created['id']}/permissions",
        json={"permission_ids": [str(pid) for pid in perm_ids]},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    assigned_codes = {p["code"] for p in response.json()["permissions"]}
    assert {"roles.list", "roles.view"}.issubset(assigned_codes)


@pytest.mark.asyncio
async def test_get_roles_with_permission(
    client: AsyncClient, user_with_roles_permissions: str
):
    response = await client.get(
        "/api/v1/roles",
        headers={"X-Session-Key": user_with_roles_permissions},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_roles_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    response = await client.get(
        "/api/v1/roles",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_role_with_permission(
    client: AsyncClient, user_with_roles_permissions: str
):
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
    create_response = await client.post(
        "/api/v1/roles",
        json={"name": "Test Role"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    perms = (
        await client.get(
            "/api/v1/permissions", headers={"X-Session-Key": superuser_token}
        )
    ).json()

    response = await client.post(
        f"/api/v1/roles/{created['id']}/permissions",
        json={"permission_ids": [perms[0]["id"]]},
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403
