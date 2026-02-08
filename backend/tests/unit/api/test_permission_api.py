import os
import sys
from uuid import uuid4

import pytest

sys.path.append(f"{os.getcwd()}/src")
from auth.models import Permission
from auth.permissions.api import get_permissions
from auth.permissions.fakes import FakePermissionService


@pytest.fixture
def permission_service():
    """Provide a fake permission service with test data."""
    service = FakePermissionService()
    # Add active permissions
    service.permissions[uuid4()] = Permission(
        id=uuid4(), name="Perm 1", code="perm.1", is_active=True
    )
    service.permissions[uuid4()] = Permission(
        id=uuid4(), name="Perm 2", code="perm.2", is_active=True
    )
    # Add inactive permission
    service.permissions[uuid4()] = Permission(
        id=uuid4(), name="Perm 3", code="perm.3", is_active=False
    )
    return service


@pytest.mark.asyncio
async def test_get_permissions_returns_all_active(permission_service):
    """Test GET /permissions endpoint returns all active permissions."""
    result = await get_permissions(permission_service=permission_service)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(p.is_active for p in result)


@pytest.mark.asyncio
async def test_get_permissions_excludes_inactive(permission_service):
    """Test GET /permissions endpoint excludes inactive permissions."""
    result = await get_permissions(permission_service=permission_service)

    assert isinstance(result, list)
    assert all(p.code != "perm.3" for p in result)


@pytest.mark.asyncio
async def test_get_permissions_empty_list():
    """Test GET /permissions endpoint with no permissions."""
    service = FakePermissionService()
    result = await get_permissions(permission_service=service)

    assert isinstance(result, list)
    assert len(result) == 0
