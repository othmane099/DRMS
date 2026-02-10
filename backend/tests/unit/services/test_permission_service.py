import os
import sys
from uuid import UUID, uuid4

import pytest

sys.path.append(f"{os.getcwd()}/src")

from auth.models import Permission
from auth.permissions.service import PermissionServiceImpl
from unit_of_work.fake_uow import FakeUnitOfWork


@pytest.fixture
def uow():
    return FakeUnitOfWork()


@pytest.fixture
def service(uow):
    return PermissionServiceImpl(unit_of_work=uow)


def _add_permission(uow, code: str, is_active: bool = True) -> Permission:
    perm_id = uuid4()
    perm = Permission(id=perm_id, name=code, code=code, is_active=is_active)
    uow.permission_repository.permissions[perm_id] = perm
    return perm


def _assign_to_role(uow, role_id: UUID, permission: Permission) -> None:
    uow.permission_repository.role_permissions.setdefault(
        UUID(str(role_id)), set()
    ).add(UUID(str(permission.id)))


@pytest.mark.asyncio
async def test_get_all_permissions_returns_active_only(service, uow):
    _add_permission(uow, "perm.read")
    _add_permission(uow, "perm.write")
    _add_permission(uow, "perm.delete", is_active=False)

    result = await service.get_all_permissions()

    assert len(result) == 2
    assert all(p.is_active for p in result)


@pytest.mark.asyncio
async def test_get_all_permissions_empty(service):
    result = await service.get_all_permissions()

    assert result == []


@pytest.mark.asyncio
async def test_get_permissions_by_role_id_returns_assigned(service, uow):
    role_id = uuid4()
    assigned = _add_permission(uow, "perm.read")
    _add_permission(uow, "perm.write")  # not assigned to role
    _assign_to_role(uow, role_id, assigned)

    result = await service.get_permissions_by_role_id(role_id)

    assert len(result) == 1
    assert result[0].code == "perm.read"


@pytest.mark.asyncio
async def test_get_permissions_by_role_id_returns_empty_for_unknown_role(service, uow):
    _add_permission(uow, "perm.read")

    result = await service.get_permissions_by_role_id(uuid4())

    assert result == []


@pytest.mark.asyncio
async def test_get_permissions_by_role_id_excludes_inactive(service, uow):
    role_id = uuid4()
    active = _add_permission(uow, "perm.read")
    inactive = _add_permission(uow, "perm.write", is_active=False)
    _assign_to_role(uow, role_id, active)
    _assign_to_role(uow, role_id, inactive)

    result = await service.get_permissions_by_role_id(role_id)

    assert len(result) == 1
    assert result[0].code == "perm.read"
