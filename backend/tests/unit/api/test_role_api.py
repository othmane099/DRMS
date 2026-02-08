import os
import sys

import pytest
from fastapi import HTTPException
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from auth.permissions.fakes import FakePermissionService
from auth.roles.api import (
    create_role,
    delete_role,
    get_role,
    get_roles,
    update_role,
    update_role_status,
)
from auth.roles.fakes import FakeRoleService
from auth.roles.schemas import RoleCreate, RoleStatusUpdate, RoleUpdate
from auth.users.fakes import FakeUserService


@pytest.fixture
def permission_service():
    """Provide a fake permission service."""
    return FakePermissionService()


@pytest.fixture
def user_service():
    """Provide a fake user service."""
    return FakeUserService()


@pytest.fixture
def role_service(permission_service, user_service):
    """Provide a fake role service."""
    return FakeRoleService(
        permission_service=permission_service, user_service=user_service
    )


@pytest.mark.asyncio
async def test_get_roles_api(role_service):
    """Test GET /roles endpoint."""
    await role_service.create_role(
        RoleCreate(name="Admin", description="Admin role", is_active=True)
    )
    await role_service.create_role(
        RoleCreate(name="User", description="User role", is_active=True)
    )

    result = await get_roles(role_service=role_service)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_role_api_success(role_service):
    """Test GET /roles/{id} endpoint with valid ID."""
    created = await role_service.create_role(
        RoleCreate(name="Manager", description="Manager role", is_active=True)
    )

    result = await get_role(role_id=created.id, role_service=role_service)

    assert result.id == created.id
    assert result.name == "Manager"


@pytest.mark.asyncio
async def test_get_role_api_not_found(role_service):
    """Test GET /roles/{id} endpoint with invalid ID."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await get_role(role_id=uuid4(), role_service=role_service)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_role_api_success(role_service):
    """Test POST /roles endpoint."""
    role_data = RoleCreate(name="Editor", description="Editor role", is_active=True)

    result = await create_role(role_create=role_data, role_service=role_service)

    assert result.name == "Editor"
    assert result.description == "Editor role"
    assert result.is_active is True


@pytest.mark.asyncio
async def test_create_role_api_duplicate(role_service):
    """Test POST /roles endpoint with duplicate name."""
    role_data = RoleCreate(name="Duplicate", description="Dup role", is_active=True)

    await role_service.create_role(role_data)

    with pytest.raises(HTTPException) as exc_info:
        await create_role(role_create=role_data, role_service=role_service)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_role_api_success(role_service):
    """Test PUT /roles/{id} endpoint."""
    created = await role_service.create_role(
        RoleCreate(name="Old Name", description="Old desc", is_active=True)
    )

    update_data = RoleUpdate(name="New Name", description="New desc")

    result = await update_role(
        role_id=created.id, role_update=update_data, role_service=role_service
    )

    assert result.name == "New Name"
    assert result.description == "New desc"
    assert result.is_active is True


@pytest.mark.asyncio
async def test_update_role_api_not_found(role_service):
    """Test PUT /roles/{id} endpoint with invalid ID."""
    from uuid import uuid4

    update_data = RoleUpdate(name="Update", description="Update desc")

    with pytest.raises(HTTPException) as exc_info:
        await update_role(
            role_id=uuid4(), role_update=update_data, role_service=role_service
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_role_api_success(role_service):
    """Test DELETE /roles/{id} endpoint."""
    created = await role_service.create_role(
        RoleCreate(name="Delete Me", description="Delete role", is_active=True)
    )

    result = await delete_role(role_id=created.id, role_service=role_service)

    assert "deleted successfully" in result.detail.lower()


@pytest.mark.asyncio
async def test_delete_role_api_not_found(role_service):
    """Test DELETE /roles/{id} endpoint with invalid ID."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await delete_role(role_id=uuid4(), role_service=role_service)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_role_status_api_deactivate_success(role_service):
    """Test PUT /roles/{id}/status endpoint to deactivate a role."""
    created = await role_service.create_role(
        RoleCreate(name="Active Role", description="Active role", is_active=True)
    )

    status_update = RoleStatusUpdate(is_active=False)
    result = await update_role_status(
        role_id=created.id, status_update=status_update, role_service=role_service
    )

    assert result.is_active is False


@pytest.mark.asyncio
async def test_update_role_status_api_activate_success(role_service):
    """Test PUT /roles/{id}/status endpoint to activate a role."""
    created = await role_service.create_role(
        RoleCreate(name="Inactive Role", description="Inactive role", is_active=False)
    )

    status_update = RoleStatusUpdate(is_active=True)
    result = await update_role_status(
        role_id=created.id, status_update=status_update, role_service=role_service
    )

    assert result.is_active is True


@pytest.mark.asyncio
async def test_update_role_status_api_not_found(role_service):
    """Test PUT /roles/{id}/status endpoint with invalid ID."""
    from uuid import uuid4

    status_update = RoleStatusUpdate(is_active=False)

    with pytest.raises(HTTPException) as exc_info:
        await update_role_status(
            role_id=uuid4(), status_update=status_update, role_service=role_service
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
