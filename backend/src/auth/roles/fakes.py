from datetime import datetime
from typing import Any
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
    def __init__(self, session: Any = None):
        self.session = session
        self.roles: dict[UUID, Role] = {}
        self.permissions: dict[UUID, Permission] = {}

    async def get_all_roles(self, only_active: bool = True) -> list[Role]:
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
        pass

    async def get_permissions_by_codes(
        self, permission_codes: list[str]
    ) -> list[Permission]:
        return [
            p
            for p in self.permissions.values()
            if p.code in permission_codes and p.is_active
        ]

    async def delete_role(self, role: Role) -> None:
        if role.id in self.roles:
            del self.roles[role.id]


class FakeRoleService(RoleService):
    def __init__(
        self,
        permission_service: Any | None = None,
        user_service: Any | None = None,
    ):
        self.roles: dict[UUID, Role] = {}
        self._permission_service = permission_service
        self._user_service = user_service

    async def get_all_roles(self) -> list[RoleResponse]:
        role_responses = []
        for role in self.roles.values():
            if role.is_active:
                # Get permission count from service
                permission_count = 0
                if self._permission_service:
                    permission_count = (
                        await self._permission_service.get_permission_count_by_role_id(
                            role.id
                        )
                    )

                # Get user count from service
                user_count = 0
                if self._user_service:
                    user_count = await self._user_service.count_users_by_role_id(
                        role.id
                    )

                role_responses.append(
                    RoleResponse(
                        id=role.id,
                        name=role.name,
                        description=role.description,
                        is_active=role.is_active,
                        permission_count=permission_count,
                        user_count=user_count,
                        created_at=role.created_at,
                        updated_at=role.updated_at,
                    )
                )
        return role_responses

    async def get_role_by_id(self, role_id: UUID) -> Role | Error:
        role = self.roles.get(role_id)
        if role:
            return role
        return Error(detail="Role not found", code=status.HTTP_404_NOT_FOUND)

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
        existing_role = await self.get_role_by_id(role_id)
        if isinstance(existing_role, Error):
            return existing_role

        if existing_role.name != role_update.name:
            conflict = await self.get_role_by_name(role_update.name)
            if not isinstance(conflict, Error):
                return Error(
                    detail="Role name already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

        role = self.roles[role_id]
        role.name = role_update.name
        role.description = role_update.description
        return role

    async def delete_role(self, role_id: UUID4) -> Message | Error:
        role = self.roles.get(role_id)
        if not role:
            return Error(detail="Role not found", code=status.HTTP_404_NOT_FOUND)

        # Get user count from service
        user_count = 0
        if self._user_service:
            user_count = await self._user_service.count_users_by_role_id(role_id)

        if user_count > 0:
            return Error(
                detail=f"Cannot delete role. {user_count} user(s) are assigned to this role",
                code=status.HTTP_400_BAD_REQUEST,
            )

        del self.roles[role_id]
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
        return role
