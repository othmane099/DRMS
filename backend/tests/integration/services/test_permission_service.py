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
def service():
    uow = UnitOfWorkImpl(session_factory=default_session_factory)
    return PermissionServiceImpl(unit_of_work=uow)


async def _create_role(permission_codes: list[str]) -> Role:
    async with default_session_factory() as db:
        result = await db.execute(
            select(Permission).where(Permission.code.in_(permission_codes))
        )
        permissions = list(result.scalars().all())
        role = Role(name=f"Role {permission_codes}", is_active=True)
        role.permissions = permissions
        db.add(role)
        await db.commit()
        return role


async def _deactivate_permission(code: str) -> None:
    async with default_session_factory() as db:
        result = await db.execute(select(Permission).where(Permission.code == code))
        permission = result.scalar_one()
        permission.is_active = False
        await db.commit()


@pytest.mark.asyncio
async def test_get_all_permissions_returns_seeded_data(service):
    result = await service.get_all_permissions()

    assert len(result) > 0
    codes = {p.code for p in result}
    assert {
        "permissions.list",
        "roles.list",
        "users.list",
        "logged_histories.view",
    }.issubset(codes)


@pytest.mark.asyncio
async def test_get_all_permissions_excludes_inactive(service):
    await _deactivate_permission("permissions.list")

    result = await service.get_all_permissions()

    assert all(p.code != "permissions.list" for p in result)


@pytest.mark.asyncio
async def test_get_permissions_by_role_id_returns_assigned(service):
    role = await _create_role(["roles.list", "roles.view", "roles.create"])

    result = await service.get_permissions_by_role_id(role.id)

    assert {p.code for p in result} == {"roles.list", "roles.view", "roles.create"}


@pytest.mark.asyncio
async def test_get_permissions_by_role_id_returns_empty_for_role_with_no_permissions(
    service,
):
    async with default_session_factory() as db:
        role = Role(name="Empty Role", is_active=True)
        db.add(role)
        await db.commit()
        role_id = role.id

    result = await service.get_permissions_by_role_id(role_id)

    assert result == []


@pytest.mark.asyncio
async def test_get_permissions_by_role_id_excludes_inactive(service):
    role = await _create_role(["users.list", "users.view"])
    await _deactivate_permission("users.list")

    result = await service.get_permissions_by_role_id(role.id)

    assert len(result) == 1
    assert result[0].code == "users.view"
