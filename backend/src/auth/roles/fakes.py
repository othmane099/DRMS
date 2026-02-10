from datetime import datetime
from uuid import UUID, uuid4

from pydantic import UUID4
from starlette import status

from auth.models import Permission, Role
from auth.roles.repository import RoleRepository
from auth.roles.schemas import (
    AssignPermissionsRequest,
    RoleCreate,
    RoleResponse,
    RoleStatusUpdate,
    RoleUpdate,
)
from auth.roles.service import RoleService
from schemas import Error, Message


class FakeRoleRepository(RoleRepository):
    def __init__(self):
        self.roles: dict[UUID, Role] = {}
        self.permissions: dict[UUID, Permission] = {}

    async def get_all_roles(self, only_active: bool = False) -> list[Role]:
        if only_active:
            return [r for r in self.roles.values() if r.is_active]
        return list(self.roles.values())

    async def get_role_by_id(
        self, role_id: UUID4, only_active: bool = False
    ) -> Role | None:
        role = self.roles.get(role_id)
        if role and only_active and not role.is_active:
            return None
        return role

    async def get_role_by_name(
        self, name: str, only_active: bool = False
    ) -> Role | None:
        for role in self.roles.values():
            if role.name == name:
                if only_active and not role.is_active:
                    return None
                return role
        return None

    async def create_role(self, role_create: RoleCreate) -> Role | None:
        role = Role(
            id=uuid4(),
            name=role_create.name,
            description=role_create.description,
            is_active=role_create.is_active,
            created_at=datetime.now(),
        )
        self.roles[role.id] = role
        return role

    async def assign_permissions_to_role(
        self, role: Role, permission_ids: list[UUID4]
    ) -> None:
        role.permissions = [
            p for p in self.permissions.values() if p.id in permission_ids
        ]

    async def get_permissions_by_codes(
        self, permission_codes: list[str]
    ) -> list[Permission]:
        return [
            p
            for p in self.permissions.values()
            if p.code in permission_codes and p.is_active
        ]

    async def delete_role(self, role: Role) -> None:
        self.roles.pop(role.id, None)


class FakeRoleService(RoleService):
    def __init__(self):
        self.roles: dict[UUID, Role] = {}
        self.role_permissions: dict[UUID, set[UUID]] = {}
        self.role_user_counts: dict[UUID, int] = {}

    async def get_all_roles(self) -> list[RoleResponse]:
        return [
            RoleResponse(
                id=role.id,
                name=role.name,
                description=role.description,
                is_active=role.is_active,
                permission_count=len(self.role_permissions.get(role.id, set())),
                user_count=self.role_user_counts.get(role.id, 0),
                created_at=role.created_at,
                updated_at=role.updated_at,
            )
            for role in self.roles.values()
            if role.is_active
        ]

    async def get_role_by_id(self, role_id: UUID) -> Role | Error:
        role = self.roles.get(role_id)
        if not role:
            return Error(detail="Role not found", code=status.HTTP_404_NOT_FOUND)
        return role

    async def get_role_by_name(self, name: str) -> Role | Error:
        for role in self.roles.values():
            if role.name == name:
                return role
        return Error(detail="Role not found", code=status.HTTP_404_NOT_FOUND)

    async def create_role(self, role_create: RoleCreate) -> Role | Error:
        existing = await self.get_role_by_name(role_create.name)
        if not isinstance(existing, Error):
            return Error(
                detail="Role name already exists",
                code=status.HTTP_400_BAD_REQUEST,
            )
        role = Role(
            id=uuid4(),
            name=role_create.name,
            description=role_create.description,
            is_active=role_create.is_active,
            created_at=datetime.now(),
        )
        self.roles[role.id] = role
        return role

    async def update_role(
        self, role_id: UUID4, role_update: RoleUpdate
    ) -> Role | Error:
        role = self.roles.get(role_id)
        if not role:
            return Error(detail="Role not found", code=status.HTTP_404_NOT_FOUND)

        if role.name != role_update.name:
            conflict = await self.get_role_by_name(role_update.name)
            if not isinstance(conflict, Error):
                return Error(
                    detail="Role name already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

        role.name = role_update.name
        role.description = role_update.description
        return role

    async def delete_role(self, role_id: UUID4) -> Message | Error:
        role = self.roles.get(role_id)
        if not role:
            return Error(detail="Role not found", code=status.HTTP_404_NOT_FOUND)

        user_count = self.role_user_counts.get(role_id, 0)
        if user_count > 0:
            return Error(
                detail=f"Cannot delete role. {user_count} user(s) are assigned to this role",
                code=status.HTTP_400_BAD_REQUEST,
            )

        del self.roles[role_id]
        self.role_permissions.pop(role_id, None)
        return Message(detail="Role deleted successfully")

    async def update_role_status(
        self, role_id: UUID4, status_update: RoleStatusUpdate
    ) -> Role | Error:
        role = self.roles.get(role_id)
        if not role:
            return Error(detail="Role not found", code=status.HTTP_404_NOT_FOUND)
        role.is_active = status_update.is_active
        return role

    async def assign_permissions(
        self, role_id: UUID4, request: AssignPermissionsRequest
    ) -> Role | Error:
        role = self.roles.get(role_id)
        if not role:
            return Error(detail="Role not found", code=status.HTTP_404_NOT_FOUND)
        self.role_permissions[role_id] = set(request.permission_ids)
        return role
