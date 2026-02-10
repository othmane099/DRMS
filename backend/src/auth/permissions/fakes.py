from uuid import UUID

from pydantic import UUID4

from auth.models import Permission
from auth.permissions.repository import PermissionRepository
from auth.permissions.service import PermissionService


class FakePermissionRepository(PermissionRepository):
    def __init__(self):
        self.permissions: dict[UUID, Permission] = {}
        self.role_permissions: dict[UUID, set[UUID]] = {}

    async def get_all_permissions(self) -> list[Permission]:
        return [p for p in self.permissions.values() if p.is_active]

    async def get_permissions_by_role_id(self, role_id: UUID4) -> list[Permission]:
        permission_ids = self.role_permissions.get(UUID(str(role_id)), set())
        return [
            p
            for p in self.permissions.values()
            if p.is_active and UUID(str(p.id)) in permission_ids
        ]


class FakePermissionService(PermissionService):
    def __init__(self):
        self.permissions: dict[UUID, Permission] = {}
        self.role_permissions: dict[UUID, set[UUID]] = {}

    async def get_all_permissions(self) -> list[Permission]:
        return [p for p in self.permissions.values() if p.is_active]

    async def get_permissions_by_role_id(self, role_id: UUID4) -> list[Permission]:
        permission_ids = self.role_permissions.get(UUID(str(role_id)), set())
        return [
            p
            for p in self.permissions.values()
            if p.is_active and UUID(str(p.id)) in permission_ids
        ]
