from typing import Any
from uuid import UUID

from pydantic import UUID4

from auth.models import Permission
from auth.permissions.repository import PermissionRepository
from auth.permissions.service import PermissionService


class FakePermissionRepository(PermissionRepository):
    def __init__(self, session: Any = None):
        self.session = session
        self.permissions: dict[UUID, Permission] = {}

    async def get_all_permissions(self) -> list[Permission]:
        return [p for p in self.permissions.values() if p.is_active]

    async def get_permissions_by_role_id(self, role_id: UUID4) -> list[Permission]:
        # Simplified - in real implementation would check role_permissions table
        return [p for p in self.permissions.values() if p.is_active]


class FakePermissionService(PermissionService):
    def __init__(self):
        self.permissions: dict[UUID, Permission] = {}

    async def get_all_permissions(self) -> list[Permission]:
        return [p for p in self.permissions.values() if p.is_active]

    async def get_permissions_by_role_id(self, role_id: UUID4) -> list[Permission]:
        return [p for p in self.permissions.values() if p.is_active]

    async def get_permission_count_by_role_id(self, role_id: UUID4) -> int:
        return len([p for p in self.permissions.values() if p.is_active])
