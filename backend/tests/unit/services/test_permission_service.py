import os
import sys
from uuid import uuid4

import pytest

sys.path.append(f"{os.getcwd()}/src")
from auth.models import Permission
from auth.permissions.service import PermissionServiceImpl
from unit_of_work.fake_uow import FakeUnitOfWork


@pytest.fixture
def uow():
    """Provide a fake unit of work with test permissions."""
    uow = FakeUnitOfWork()
    # Add active test permissions
    for i in range(5):
        perm_id = uuid4()
        uow.permission_repository.permissions[perm_id] = Permission(
            id=perm_id, name=f"Permission {i}", code=f"perm.{i}", is_active=True
        )
    # Add inactive permissions
    for i in range(5, 7):
        perm_id = uuid4()
        uow.permission_repository.permissions[perm_id] = Permission(
            id=perm_id, name=f"Permission {i}", code=f"perm.{i}", is_active=False
        )
    return uow


@pytest.fixture
def permission_service(uow):
    """Provide a permission service with fake UoW."""
    return PermissionServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_get_all_permissions_returns_active_only(permission_service):
    """Test retrieving all active permissions."""
    result = await permission_service.get_all_permissions()

    assert len(result) == 5
    assert all(p.is_active for p in result)


@pytest.mark.asyncio
async def test_get_all_permissions_excludes_inactive(permission_service):
    """Test that inactive permissions are excluded."""
    result = await permission_service.get_all_permissions()

    assert len(result) == 5
    assert all(p.code not in ["perm.5", "perm.6"] for p in result)


@pytest.mark.asyncio
async def test_get_all_permissions_empty():
    """Test retrieving permissions when none exist."""
    uow = FakeUnitOfWork()
    service = PermissionServiceImpl(unit_of_work=uow)

    result = await service.get_all_permissions()

    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_permissions_by_role_id(permission_service):
    """Test retrieving permissions by role ID (simplified in fake)."""
    role_id = uuid4()

    result = await permission_service.get_permissions_by_role_id(role_id)

    assert len(result) == 5
    assert all(p.is_active for p in result)
