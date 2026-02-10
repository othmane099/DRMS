import os
import sys
from uuid import uuid4

import pytest
from starlette import status

sys.path.append(f"{os.getcwd()}/src")

from auth.models import Permission  # noqa: E402
from auth.roles.fakes import FakeRoleRepository  # noqa: E402
from auth.roles.schemas import (  # noqa: E402
    AssignPermissionsRequest,
    RoleCreate,
    RoleStatusUpdate,
    RoleUpdate,
)
from auth.roles.service import RoleServiceImpl  # noqa: E402
from schemas import Error, Message  # noqa: E402
from unit_of_work.fake_uow import FakeUnitOfWork  # noqa: E402


@pytest.fixture
def uow():
    return FakeUnitOfWork()


@pytest.fixture
def service(uow):
    return RoleServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_create_role_success(service):
    """Test creating a new role successfully."""
    result = await service.create_role(
        RoleCreate(name="Admin", description="Administrator role", is_active=True)
    )

    assert not isinstance(result, Error)
    assert result.name == "Admin"
    assert result.description == "Administrator role"
    assert result.is_active is True


@pytest.mark.asyncio
async def test_create_role_duplicate_name(service):
    """Test creating a role with duplicate name fails."""
    role_data = RoleCreate(name="Manager", description="Manager role", is_active=True)
    await service.create_role(role_data)

    result = await service.create_role(role_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_role_by_id_success(service):
    """Test retrieving a role by ID."""
    created = await service.create_role(
        RoleCreate(name="Editor", description="Editor role", is_active=True)
    )
    assert not isinstance(created, Error)

    result = await service.get_role_by_id(created.id)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.name == "Editor"


@pytest.mark.asyncio
async def test_get_role_by_id_not_found(service):
    """Test retrieving a non-existent role returns error."""
    result = await service.get_role_by_id(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_role_by_name_success(service):
    """Test retrieving a role by name."""
    await service.create_role(
        RoleCreate(name="Viewer", description="Viewer role", is_active=True)
    )

    result = await service.get_role_by_name("Viewer")

    assert not isinstance(result, Error)
    assert result.name == "Viewer"


@pytest.mark.asyncio
async def test_get_all_roles(service):
    """Test retrieving all roles."""
    for i in range(3):
        await service.create_role(
            RoleCreate(name=f"Role {i}", description=f"Desc {i}", is_active=True)
        )

    result = await service.get_all_roles()

    assert len(result) == 3


@pytest.mark.asyncio
async def test_update_role_success(service):
    """Test updating a role successfully."""
    created = await service.create_role(
        RoleCreate(
            name="Support", description="Support role", is_active=True, permissions=[]
        )
    )
    assert not isinstance(created, Error)

    result = await service.update_role(
        created.id,
        RoleUpdate(
            name="Customer Support", description="Customer support role", permissions=[]
        ),
    )

    assert not isinstance(result, Error)
    assert result.name == "Customer Support"
    assert result.description == "Customer support role"


@pytest.mark.asyncio
async def test_update_role_not_found(service):
    """Test updating a non-existent role returns error."""
    result = await service.update_role(
        uuid4(), RoleUpdate(name="Updated", description="Updated role")
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_role_duplicate_name(service):
    """Test updating role to existing name fails."""
    created1 = await service.create_role(
        RoleCreate(name="Role 1", description="First role", is_active=True)
    )
    created2 = await service.create_role(
        RoleCreate(name="Role 2", description="Second role", is_active=True)
    )
    assert not isinstance(created1, Error)
    assert not isinstance(created2, Error)

    result = await service.update_role(
        created2.id, RoleUpdate(name="Role 1", description="Updated")
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_delete_role_success(service):
    """Test deleting a role (hard delete)."""
    created = await service.create_role(
        RoleCreate(name="Temporary", description="Temp role", is_active=True)
    )
    assert not isinstance(created, Error)

    result = await service.delete_role(created.id)

    assert isinstance(result, Message)
    assert "deleted successfully" in result.detail.lower()

    get_result = await service.get_role_by_id(created.id)
    assert isinstance(get_result, Error)


@pytest.mark.asyncio
async def test_delete_role_not_found(service):
    """Test deleting a non-existent role returns error."""
    result = await service.delete_role(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_role_status_deactivate_success(service):
    """Test deactivating a role successfully."""
    created = await service.create_role(
        RoleCreate(name="Active Role", description="Active role", is_active=True)
    )
    assert not isinstance(created, Error)
    assert created.is_active is True

    result = await service.update_role_status(
        created.id, RoleStatusUpdate(is_active=False)
    )

    assert not isinstance(result, Error)
    assert result.is_active is False


@pytest.mark.asyncio
async def test_update_role_status_activate_success(service):
    """Test activating a role successfully."""
    created = await service.create_role(
        RoleCreate(name="Inactive Role", description="Inactive role", is_active=False)
    )
    assert not isinstance(created, Error)
    assert created.is_active is False

    result = await service.update_role_status(
        created.id, RoleStatusUpdate(is_active=True)
    )

    assert not isinstance(result, Error)
    assert result.is_active is True


@pytest.mark.asyncio
async def test_update_role_status_not_found(service):
    """Test updating status of non-existent role returns error."""
    result = await service.update_role_status(
        uuid4(), RoleStatusUpdate(is_active=False)
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND


def _add_permission(uow: FakeUnitOfWork, code: str) -> Permission:
    perm_id = uuid4()
    perm = Permission(id=perm_id, name=code, code=code, is_active=True)
    repo: FakeRoleRepository = uow.role_repository  # type: ignore[assignment]
    repo.permissions[perm_id] = perm
    return perm


@pytest.mark.asyncio
async def test_assign_permissions_success(service, uow):
    """Test assigning permissions to a role successfully."""
    created = await service.create_role(
        RoleCreate(name="Editor", description="Editor role", is_active=True)
    )
    assert not isinstance(created, Error)
    perm1 = _add_permission(uow, "docs.read")
    perm2 = _add_permission(uow, "docs.write")

    result = await service.assign_permissions(
        created.id, AssignPermissionsRequest(permission_ids=[perm1.id, perm2.id])
    )

    assert not isinstance(result, Error)
    assert {p.id for p in result.permissions} == {perm1.id, perm2.id}


@pytest.mark.asyncio
async def test_assign_permissions_not_found(service):
    """Test assigning permissions to a non-existent role returns error."""
    result = await service.assign_permissions(
        uuid4(), AssignPermissionsRequest(permission_ids=[uuid4()])
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_assign_permissions_empty_clears_permissions(service, uow):
    """Test assigning an empty list clears existing permissions."""
    created = await service.create_role(
        RoleCreate(name="Viewer", description="Viewer role", is_active=True)
    )
    assert not isinstance(created, Error)
    perm = _add_permission(uow, "docs.read")
    await service.assign_permissions(
        created.id, AssignPermissionsRequest(permission_ids=[perm.id])
    )

    result = await service.assign_permissions(
        created.id, AssignPermissionsRequest(permission_ids=[])
    )

    assert not isinstance(result, Error)
    assert result.permissions == []


@pytest.mark.asyncio
async def test_assign_permissions_unknown_ids_ignored(service, uow):
    """Test that unknown permission IDs are silently ignored."""
    created = await service.create_role(
        RoleCreate(name="Manager", description="Manager role", is_active=True)
    )
    assert not isinstance(created, Error)
    known = _add_permission(uow, "docs.read")

    result = await service.assign_permissions(
        created.id,
        AssignPermissionsRequest(permission_ids=[known.id, uuid4()]),
    )

    assert not isinstance(result, Error)
    assert len(result.permissions) == 1
    assert result.permissions[0].id == known.id
