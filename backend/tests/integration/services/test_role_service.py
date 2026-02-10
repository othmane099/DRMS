import os
import sys

import pytest
from sqlalchemy import select

sys.path.insert(0, f"{os.getcwd()}/src")

from auth.models import Permission, Role  # noqa: E402
from auth.roles.schemas import (  # noqa: E402
    AssignPermissionsRequest,
    RoleCreate,
    RoleStatusUpdate,
    RoleUpdate,
)
from auth.roles.service import RoleServiceImpl  # noqa: E402
from db import default_session_factory  # noqa: E402
from schemas import Error  # noqa: E402
from unit_of_work.uow import UnitOfWorkImpl  # noqa: E402


@pytest.fixture
def service():
    uow = UnitOfWorkImpl(session_factory=default_session_factory)
    return RoleServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_create_role_commits_to_database(service):
    """Test that creating a role commits data to database."""
    result = await service.create_role(
        RoleCreate(name="Administrator", description="Admin role", is_active=True)
    )

    assert not isinstance(result, Error)

    async with default_session_factory() as db:
        db_role = (
            await db.execute(select(Role).where(Role.id == result.id))
        ).scalar_one_or_none()

        assert db_role is not None
        assert db_role.name == "Administrator"
        assert db_role.description == "Admin role"
        assert db_role.is_active is True


@pytest.mark.asyncio
async def test_update_role_commits_to_database(service):
    """Test that updating a role commits changes to database."""
    created = await service.create_role(
        RoleCreate(name="Manager", description="Manager role", is_active=True)
    )
    assert not isinstance(created, Error)

    result = await service.update_role(
        created.id, RoleUpdate(name="Senior Manager", description="Senior manager role")
    )
    assert not isinstance(result, Error)

    async with default_session_factory() as db:
        db_role = (
            await db.execute(select(Role).where(Role.id == created.id))
        ).scalar_one_or_none()

        assert db_role is not None
        assert db_role.name == "Senior Manager"
        assert db_role.description == "Senior manager role"


@pytest.mark.asyncio
async def test_delete_role_hard_deletes_in_database(service):
    """Test that deleting a role removes it from database (hard delete)."""
    created = await service.create_role(
        RoleCreate(name="Temp Role", description="Temporary", is_active=True)
    )
    assert not isinstance(created, Error)

    result = await service.delete_role(created.id)
    assert not isinstance(result, Error)

    async with default_session_factory() as db:
        db_role = (
            await db.execute(select(Role).where(Role.id == created.id))
        ).scalar_one_or_none()

        assert db_role is None


@pytest.mark.asyncio
async def test_update_role_status_commits_to_database(service):
    """Test that updating role status commits changes to database."""
    created = await service.create_role(
        RoleCreate(name="Test Role", description="Test role", is_active=True)
    )
    assert not isinstance(created, Error)

    result = await service.update_role_status(
        created.id, RoleStatusUpdate(is_active=False)
    )
    assert not isinstance(result, Error)

    async with default_session_factory() as db:
        db_role = (
            await db.execute(select(Role).where(Role.id == created.id))
        ).scalar_one_or_none()

        assert db_role is not None
        assert db_role.is_active is False


@pytest.mark.asyncio
async def test_update_role_status_activate_commits_to_database(service):
    """Test that activating a role commits changes to database."""
    created = await service.create_role(
        RoleCreate(name="Inactive Test", description="Inactive", is_active=False)
    )
    assert not isinstance(created, Error)

    result = await service.update_role_status(
        created.id, RoleStatusUpdate(is_active=True)
    )
    assert not isinstance(result, Error)

    async with default_session_factory() as db:
        db_role = (
            await db.execute(select(Role).where(Role.id == created.id))
        ).scalar_one_or_none()

        assert db_role is not None
        assert db_role.is_active is True


@pytest.mark.asyncio
async def test_assign_permissions_commits_to_database(service):
    """Test that assigning permissions to a role persists in database."""
    created = await service.create_role(
        RoleCreate(
            name="Managed Role", description="Role with permissions", is_active=True
        )
    )
    assert not isinstance(created, Error)

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

    result = await service.assign_permissions(
        created.id, AssignPermissionsRequest(permission_ids=list(perm_ids))
    )
    assert not isinstance(result, Error)

    async with default_session_factory() as db:
        db_role = (
            await db.execute(select(Role).where(Role.id == created.id))
        ).scalar_one_or_none()
        await db.refresh(db_role, ["permissions"])

        assert {p.id for p in db_role.permissions} == set(perm_ids)
