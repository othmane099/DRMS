import os
import sys

import pytest
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from auth.roles.schemas import RoleCreate, RoleStatusUpdate, RoleUpdate
from auth.roles.service import RoleServiceImpl
from schemas import Error, Message
from unit_of_work.fake_uow import FakeUnitOfWork


@pytest.fixture
def uow():
    """Provide a fake unit of work."""
    return FakeUnitOfWork()


@pytest.fixture
def role_service(uow):
    """Provide a role service with fake UoW and services."""
    return RoleServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_create_role_success(role_service):
    """Test creating a new role successfully."""
    role_data = RoleCreate(
        name="Admin", description="Administrator role", is_active=True
    )

    result = await role_service.create_role(role_data)

    assert not isinstance(result, Error)
    assert result.name == "Admin"
    assert result.description == "Administrator role"
    assert result.is_active is True


@pytest.mark.asyncio
async def test_create_role_duplicate_name(role_service):
    """Test creating a role with duplicate name fails."""
    role_data = RoleCreate(name="Manager", description="Manager role", is_active=True)

    await role_service.create_role(role_data)

    result = await role_service.create_role(role_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_role_by_id_success(role_service):
    """Test retrieving a role by ID."""
    role_data = RoleCreate(name="Editor", description="Editor role", is_active=True)

    created = await role_service.create_role(role_data)
    assert not isinstance(created, Error)

    result = await role_service.get_role_by_id(created.id)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.name == "Editor"


@pytest.mark.asyncio
async def test_get_role_by_id_not_found(role_service):
    """Test retrieving a non-existent role returns error."""
    from uuid import uuid4

    result = await role_service.get_role_by_id(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_role_by_name_success(role_service):
    """Test retrieving a role by name."""
    role_data = RoleCreate(name="Viewer", description="Viewer role", is_active=True)

    await role_service.create_role(role_data)

    result = await role_service.get_role_by_name("Viewer")

    assert not isinstance(result, Error)
    assert result.name == "Viewer"


@pytest.mark.asyncio
async def test_update_role_success(role_service):
    """Test updating a role successfully."""
    role_data = RoleCreate(
        name="Support", description="Support role", is_active=True, permissions=[]
    )

    created = await role_service.create_role(role_data)
    assert not isinstance(created, Error)

    update_data = RoleUpdate(
        name="Customer Support",
        description="Customer support role",
        permissions=[],
    )

    result = await role_service.update_role(created.id, update_data)

    assert not isinstance(result, Error)
    assert result.name == "Customer Support"
    assert result.description == "Customer support role"


@pytest.mark.asyncio
async def test_update_role_not_found(role_service):
    """Test updating a non-existent role returns error."""
    from uuid import uuid4

    update_data = RoleUpdate(name="Updated", description="Updated role")

    result = await role_service.update_role(uuid4(), update_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_role_duplicate_name(role_service):
    """Test updating role to existing name fails."""
    role1 = RoleCreate(name="Role 1", description="First role", is_active=True)
    role2 = RoleCreate(name="Role 2", description="Second role", is_active=True)

    created1 = await role_service.create_role(role1)
    created2 = await role_service.create_role(role2)
    assert not isinstance(created1, Error)
    assert not isinstance(created2, Error)

    update_data = RoleUpdate(name="Role 1", description="Updated", is_active=True)
    result = await role_service.update_role(created2.id, update_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_delete_role_success(role_service):
    """Test deleting a role (hard delete)."""
    role_data = RoleCreate(name="Temporary", description="Temp role", is_active=True)

    created = await role_service.create_role(role_data)
    assert not isinstance(created, Error)

    result = await role_service.delete_role(created.id)

    assert isinstance(result, Message)
    assert "deleted successfully" in result.detail.lower()

    get_result = await role_service.get_role_by_id(created.id)
    assert isinstance(get_result, Error)


@pytest.mark.asyncio
async def test_delete_role_not_found(role_service):
    """Test deleting a non-existent role returns error."""
    from uuid import uuid4

    result = await role_service.delete_role(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_all_roles(role_service):
    """Test retrieving all roles."""
    for i in range(3):
        role_data = RoleCreate(
            name=f"Role {i}", description=f"Desc {i}", is_active=True
        )
        await role_service.create_role(role_data)

    result = await role_service.get_all_roles()

    assert len(result) == 3


@pytest.mark.asyncio
async def test_update_role_status_deactivate_success(role_service):
    """Test deactivating a role successfully."""
    role_data = RoleCreate(
        name="Active Role", description="Active role", is_active=True
    )

    created = await role_service.create_role(role_data)
    assert not isinstance(created, Error)
    assert created.is_active is True

    status_update = RoleStatusUpdate(is_active=False)
    result = await role_service.update_role_status(created.id, status_update)

    assert not isinstance(result, Error)
    assert result.is_active is False


@pytest.mark.asyncio
async def test_update_role_status_activate_success(role_service):
    """Test activating a role successfully."""
    role_data = RoleCreate(
        name="Inactive Role", description="Inactive role", is_active=False
    )

    created = await role_service.create_role(role_data)
    assert not isinstance(created, Error)
    assert created.is_active is False

    status_update = RoleStatusUpdate(is_active=True)
    result = await role_service.update_role_status(created.id, status_update)

    assert not isinstance(result, Error)
    assert result.is_active is True


@pytest.mark.asyncio
async def test_update_role_status_not_found(role_service):
    """Test updating status of non-existent role returns error."""
    from uuid import uuid4

    status_update = RoleStatusUpdate(is_active=False)
    result = await role_service.update_role_status(uuid4(), status_update)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
