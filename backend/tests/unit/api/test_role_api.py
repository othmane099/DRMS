import os
import sys
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette import status

sys.path.append(f"{os.getcwd()}/src")

from auth.roles.api import (
    assign_permissions_to_role,
    create_role,
    delete_role,
    get_role,
    get_roles,
    update_role,
    update_role_status,
)
from auth.roles.fakes import FakeRoleService
from auth.roles.schemas import (
    AssignPermissionsRequest,
    RoleCreate,
    RoleStatusUpdate,
    RoleUpdate,
)


@pytest.fixture
def service():
    return FakeRoleService()


@pytest.mark.asyncio
async def test_get_roles(service):
    await service.create_role(
        RoleCreate(name="Admin", description="Admin role", is_active=True)
    )
    await service.create_role(
        RoleCreate(name="User", description="User role", is_active=True)
    )

    result = await get_roles(role_service=service)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_role_success(service):
    """Test GET /roles/{id} endpoint with valid ID."""
    created = await service.create_role(
        RoleCreate(name="Manager", description="Manager role", is_active=True)
    )

    result = await get_role(role_id=created.id, role_service=service)

    assert result.id == created.id
    assert result.name == "Manager"


@pytest.mark.asyncio
async def test_get_role_not_found(service):
    """Test GET /roles/{id} endpoint with invalid ID."""
    with pytest.raises(HTTPException) as exc_info:
        await get_role(role_id=uuid4(), role_service=service)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_role_success(service):
    """Test POST /roles endpoint."""
    result = await create_role(
        role_create=RoleCreate(
            name="Editor", description="Editor role", is_active=True
        ),
        role_service=service,
    )

    assert result.name == "Editor"
    assert result.description == "Editor role"
    assert result.is_active is True


@pytest.mark.asyncio
async def test_create_role_duplicate(service):
    """Test POST /roles endpoint with duplicate name."""
    role_data = RoleCreate(name="Duplicate", description="Dup role", is_active=True)
    await service.create_role(role_data)

    with pytest.raises(HTTPException) as exc_info:
        await create_role(role_create=role_data, role_service=service)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_role_success(service):
    """Test PUT /roles/{id} endpoint."""
    created = await service.create_role(
        RoleCreate(name="Old Name", description="Old desc", is_active=True)
    )

    result = await update_role(
        role_id=created.id,
        role_update=RoleUpdate(name="New Name", description="New desc"),
        role_service=service,
    )

    assert result.name == "New Name"
    assert result.description == "New desc"


@pytest.mark.asyncio
async def test_update_role_not_found(service):
    """Test PUT /roles/{id} endpoint with invalid ID."""
    with pytest.raises(HTTPException) as exc_info:
        await update_role(
            role_id=uuid4(),
            role_update=RoleUpdate(name="Update", description="Update desc"),
            role_service=service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_role_success(service):
    """Test DELETE /roles/{id} endpoint."""
    created = await service.create_role(
        RoleCreate(name="Delete Me", description="Delete role", is_active=True)
    )

    result = await delete_role(role_id=created.id, role_service=service)

    assert "deleted successfully" in result.detail.lower()


@pytest.mark.asyncio
async def test_delete_role_not_found(service):
    """Test DELETE /roles/{id} endpoint with invalid ID."""
    with pytest.raises(HTTPException) as exc_info:
        await delete_role(role_id=uuid4(), role_service=service)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_role_status_deactivate(service):
    """Test PUT /roles/{id}/status endpoint to deactivate a role."""
    created = await service.create_role(
        RoleCreate(name="Active Role", description="Active role", is_active=True)
    )

    result = await update_role_status(
        role_id=created.id,
        status_update=RoleStatusUpdate(is_active=False),
        role_service=service,
    )

    assert result.is_active is False


@pytest.mark.asyncio
async def test_update_role_status_activate(service):
    """Test PUT /roles/{id}/status endpoint to activate a role."""
    created = await service.create_role(
        RoleCreate(name="Inactive Role", description="Inactive role", is_active=False)
    )

    result = await update_role_status(
        role_id=created.id,
        status_update=RoleStatusUpdate(is_active=True),
        role_service=service,
    )

    assert result.is_active is True


@pytest.mark.asyncio
async def test_update_role_status_not_found(service):
    """Test PUT /roles/{id}/status endpoint with invalid ID."""
    with pytest.raises(HTTPException) as exc_info:
        await update_role_status(
            role_id=uuid4(),
            status_update=RoleStatusUpdate(is_active=False),
            role_service=service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_assign_permissions_success(service):
    created = await service.create_role(
        RoleCreate(name="Editor", description="Editor role", is_active=True)
    )
    perm_id = uuid4()

    result = await assign_permissions_to_role(
        role_id=created.id,
        request=AssignPermissionsRequest(permission_ids=[perm_id]),
        role_service=service,
    )

    assert result.id == created.id
    assert service.role_permissions[created.id] == {perm_id}


@pytest.mark.asyncio
async def test_assign_permissions_not_found(service):
    with pytest.raises(HTTPException) as exc_info:
        await assign_permissions_to_role(
            role_id=uuid4(),
            request=AssignPermissionsRequest(permission_ids=[uuid4()]),
            role_service=service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
