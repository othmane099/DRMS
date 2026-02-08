import os
import sys

import pytest
from sqlalchemy import select

sys.path.insert(0, f"{os.getcwd()}/src")

from auth.models import Permission, Role  # noqa: E402
from auth.permissions.service import PermissionServiceImpl  # noqa: E402
from db import default_session_factory  # noqa: E402
from unit_of_work.uow import UnitOfWorkImpl  # noqa: E402


@pytest.fixture
def permission_service():
    """Provide permission service with real database."""
    uow = UnitOfWorkImpl(session_factory=default_session_factory)
    return PermissionServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_get_all_permissions_returns_seeded_data(permission_service):
    """Test that get_all_permissions returns all seeded permissions from database."""
    result = await permission_service.get_all_permissions()

    assert len(result) > 0
    assert all(isinstance(p, Permission) for p in result)

    permission_codes = {p.code for p in result}
    assert "permissions.list" in permission_codes
    assert "roles.list" in permission_codes
    assert "users.list" in permission_codes
    assert "logged_histories.view" in permission_codes


@pytest.mark.asyncio
async def test_get_all_permissions_excludes_inactive(permission_service):
    """Test that inactive permissions are excluded from results."""
    permissions = await permission_service.get_all_permissions()
    async with default_session_factory() as session:
        result = await session.execute(
            select(Permission).where(Permission.code == "permissions.list")
        )
        permission = result.scalar_one()

        permission.is_active = False
        await session.commit()

    result = await permission_service.get_all_permissions()
    assert len(result) == len(permissions) - 1
    assert all(p.code != "permissions.list" for p in result)


@pytest.mark.asyncio
async def test_get_permissions_by_role_id_returns_role_permissions(permission_service):
    """Test retrieving permissions assigned to a specific role."""
    async with default_session_factory() as session:
        result = await session.execute(
            select(Permission).where(
                Permission.code.in_(["roles.list", "roles.view", "roles.create"])
            )
        )
        permissions = list(result.scalars().all())

        role = Role(name="Test Manager", is_active=True)
        role.permissions = permissions
        session.add(role)
        await session.commit()
        role_id = role.id

    result = await permission_service.get_permissions_by_role_id(role_id)

    assert len(result) == 3
    permission_codes = {p.code for p in result}
    assert permission_codes == {"roles.list", "roles.view", "roles.create"}


@pytest.mark.asyncio
async def test_get_permissions_by_role_id_empty_role(permission_service):
    """Test retrieving permissions for a role with no permissions assigned."""
    async with default_session_factory() as session:
        role = Role(name="Empty Role", is_active=True)
        session.add(role)
        await session.commit()
        role_id = role.id

    result = await permission_service.get_permissions_by_role_id(role_id)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_permissions_by_role_id_excludes_inactive_permissions(
    permission_service,
):
    """Test that inactive permissions are excluded from role permissions."""
    async with default_session_factory() as session:
        result = await session.execute(
            select(Permission).where(Permission.code.in_(["users.list", "users.view"]))
        )
        permissions = list(result.scalars().all())

        role = Role(name="User Viewer", is_active=True)
        role.permissions = permissions
        session.add(role)
        await session.commit()
        role_id = role.id

        permissions[0].is_active = False
        await session.commit()

    result = await permission_service.get_permissions_by_role_id(role_id)

    assert len(result) == 1
    assert result[0].code == "users.view"
