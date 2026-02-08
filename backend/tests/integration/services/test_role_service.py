import os
import sys

import pytest
from sqlalchemy import select

sys.path.insert(0, f"{os.getcwd()}/src")

from auth.models import Role  # noqa: E402
from auth.permissions.service import PermissionServiceImpl  # noqa: E402
from auth.roles.schemas import RoleCreate, RoleStatusUpdate, RoleUpdate  # noqa: E402
from auth.roles.service import RoleServiceImpl  # noqa: E402
from auth.users.service import UserServiceImpl  # noqa: E402
from db import default_session_factory  # noqa: E402
from schemas import Error  # noqa: E402
from unit_of_work.uow import UnitOfWorkImpl  # noqa: E402


@pytest.fixture
def role_service():
    """Provide role service with real database."""
    uow = UnitOfWorkImpl(session_factory=default_session_factory)
    permission_service = PermissionServiceImpl(unit_of_work=uow)
    user_service = UserServiceImpl(unit_of_work=uow)
    return RoleServiceImpl(
        unit_of_work=uow,
        permission_service=permission_service,
        user_service=user_service,
    )


@pytest.mark.asyncio
async def test_create_role_commits_to_database(role_service):
    """Test that creating a role commits data to database."""
    role_data = RoleCreate(
        name="Administrator", description="Admin role", is_active=True
    )

    result = await role_service.create_role(role_data)

    assert not isinstance(result, Error)
    assert result.id is not None

    async with default_session_factory() as session:
        stmt = select(Role).where(Role.id == result.id)
        db_result = await session.execute(stmt)
        db_role = db_result.scalar_one_or_none()

        assert db_role is not None
        assert db_role.name == "Administrator"
        assert db_role.description == "Admin role"
        assert db_role.is_active is True


@pytest.mark.asyncio
async def test_update_role_commits_to_database(role_service):
    """Test that updating a role commits changes to database."""
    role_data = RoleCreate(name="Manager", description="Manager role", is_active=True)
    created = await role_service.create_role(role_data)
    assert not isinstance(created, Error)

    update_data = RoleUpdate(name="Senior Manager", description="Senior manager role")
    result = await role_service.update_role(created.id, update_data)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(Role).where(Role.id == created.id)
        db_result = await session.execute(stmt)
        db_role = db_result.scalar_one_or_none()

        assert db_role is not None
        assert db_role.name == "Senior Manager"
        assert db_role.description == "Senior manager role"
        assert db_role.is_active is True


@pytest.mark.asyncio
async def test_delete_role_hard_deletes_in_database(role_service):
    """Test that deleting a role removes it from database (hard delete)."""
    role_data = RoleCreate(name="Temp Role", description="Temporary", is_active=True)
    created = await role_service.create_role(role_data)
    assert not isinstance(created, Error)

    result = await role_service.delete_role(created.id)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(Role).where(Role.id == created.id)
        db_result = await session.execute(stmt)
        db_role = db_result.scalar_one_or_none()

        assert db_role is None


@pytest.mark.asyncio
async def test_update_role_status_commits_to_database(role_service):
    """Test that updating role status commits changes to database."""
    role_data = RoleCreate(name="Test Role", description="Test role", is_active=True)
    created = await role_service.create_role(role_data)
    assert not isinstance(created, Error)

    status_update = RoleStatusUpdate(is_active=False)
    result = await role_service.update_role_status(created.id, status_update)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(Role).where(Role.id == created.id)
        db_result = await session.execute(stmt)
        db_role = db_result.scalar_one_or_none()

        assert db_role is not None
        assert db_role.is_active is False


@pytest.mark.asyncio
async def test_update_role_status_activate_commits_to_database(role_service):
    """Test that activating a role commits changes to database."""
    role_data = RoleCreate(
        name="Inactive Test", description="Inactive", is_active=False
    )
    created = await role_service.create_role(role_data)
    assert not isinstance(created, Error)

    status_update = RoleStatusUpdate(is_active=True)
    result = await role_service.update_role_status(created.id, status_update)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(Role).where(Role.id == created.id)
        db_result = await session.execute(stmt)
        db_role = db_result.scalar_one_or_none()

        assert db_role is not None
        assert db_role.is_active is True
