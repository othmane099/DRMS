import os
import sys
from uuid import uuid4

import pytest

sys.path.insert(0, f"{os.getcwd()}/src")

from auth.models import Permission  # noqa: E402
from auth.permissions.api import get_permissions  # noqa: E402
from auth.permissions.fakes import FakePermissionService  # noqa: E402


@pytest.fixture
def service():
    return FakePermissionService()


def _add_permission(
    service: FakePermissionService, code: str, is_active: bool = True
) -> Permission:
    perm_id = uuid4()
    perm = Permission(id=perm_id, name=code, code=code, is_active=is_active)
    service.permissions[perm_id] = perm
    return perm


@pytest.mark.asyncio
async def test_returns_active_permissions(service):
    _add_permission(service, "perm.read")
    _add_permission(service, "perm.write")

    result = await get_permissions(permission_service=service)

    assert len(result) == 2
    assert all(r.is_active for r in result)


@pytest.mark.asyncio
async def test_returns_empty(service):
    result = await get_permissions(permission_service=service)

    assert result == []


@pytest.mark.asyncio
async def test_excludes_inactive_permissions(service):
    _add_permission(service, "perm.read")
    _add_permission(service, "perm.delete", is_active=False)

    result = await get_permissions(permission_service=service)

    assert len(result) == 1
    assert result[0].code == "perm.read"


@pytest.mark.asyncio
async def test_response_shape(service):
    perm = _add_permission(service, "perm.read")

    result = await get_permissions(permission_service=service)

    assert len(result) == 1
    assert result[0].id == perm.id
    assert result[0].name == perm.name
    assert result[0].code == perm.code
    assert result[0].is_active is True
