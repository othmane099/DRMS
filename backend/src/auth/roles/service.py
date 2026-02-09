import logging
from typing import Protocol
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from pydantic import UUID4
from starlette import status

from auth.models import Role
from auth.roles.schemas import (
    AssignPermissionsRequest,
    RoleCreate,
    RoleResponse,
    RoleStatusUpdate,
    RoleUpdate,
)
from schemas import Error, Message
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)


class RoleService(Protocol):
    async def get_all_roles(self) -> list[RoleResponse]: ...

    async def get_role_by_id(self, role_id: UUID) -> Role | Error: ...

    async def get_role_by_name(self, name: str) -> Role | Error: ...

    async def create_role(self, role_create: RoleCreate) -> Role | Error: ...

    async def update_role(
        self, role_id: UUID4, role_update: RoleUpdate
    ) -> Role | Error: ...

    async def delete_role(self, role_id: UUID4) -> Message | Error: ...

    async def update_role_status(
        self, role_id: UUID4, status_update: RoleStatusUpdate
    ) -> Role | Error: ...

    async def assign_permissions(
        self, role_id: UUID4, request: AssignPermissionsRequest
    ) -> Role | Error: ...


class RoleServiceImpl(RoleService):
    @inject
    def __init__(
        self,
        unit_of_work: UnitOfWork = Provide["unit_of_work"],
    ):
        self._unit_of_work = unit_of_work

    async def get_all_roles(self) -> list[RoleResponse]:
        logger.debug("Fetching all roles")
        async with self._unit_of_work as uow:
            roles = await uow.role_repository.get_all_roles()
            role_responses = []
            for role in roles:
                permissions = (
                    await uow.permission_repository.get_permissions_by_role_id(role.id)
                )
                permission_count = len(permissions)
                user_count = await uow.user_repository.count_users_by_role_id(role.id)
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
        logger.debug("Fetching role by id=%s", role_id)

        async with self._unit_of_work as uow:
            role = await uow.role_repository.get_role_by_id(role_id)
            if not role:
                logger.warning("Role not found (id=%s)", role_id)
                return Error(detail="Role not found", code=status.HTTP_404_NOT_FOUND)

            logger.debug("Role found (id=%s)", role_id)
            return role

    async def get_role_by_name(self, name: str) -> Role | Error:
        logger.debug("Fetching role by name=%s", name)

        async with self._unit_of_work as uow:
            role = await uow.role_repository.get_role_by_name(name)
            if not role:
                logger.warning("Role not found (name=%s)", name)
                return Error(detail="Role not found", code=status.HTTP_404_NOT_FOUND)

            logger.debug("Role found (name=%s)", name)
            return role

    async def create_role(self, role_create: RoleCreate) -> Role | Error:
        logger.info("Creating role (name=%s)", role_create.name)
        async with self._unit_of_work as uow:
            existing_role = await uow.role_repository.get_role_by_name(role_create.name)
            if existing_role:
                logger.warning(
                    "Role creation rejected: name already exists (name=%s)",
                    role_create.name,
                )
                return Error(
                    detail="Role name already exists", code=status.HTTP_400_BAD_REQUEST
                )

            instance = await uow.role_repository.create_role(role_create)
            await uow.commit()
            created_role = await uow.role_repository.get_role_by_id(instance.id)

        logger.info(
            "Role created successfully (id=%s, name=%s)",
            created_role.id,
            created_role.name,
        )
        return created_role

    async def update_role(
        self, role_id: UUID4, role_update: RoleUpdate
    ) -> Role | Error:
        logger.info("Updating role (id=%s)", role_id)

        async with self._unit_of_work as uow:
            existing_role = await uow.role_repository.get_role_by_id(role_id)
            if not existing_role:
                logger.warning("Role update failed: not found (id=%s)", role_id)
                return Error(detail="Role not found", code=status.HTTP_404_NOT_FOUND)

            if existing_role.name != role_update.name:
                conflict = await uow.role_repository.get_role_by_name(role_update.name)
                if conflict:
                    logger.warning(
                        "Role update rejected: name conflict (id=%s, name=%s)",
                        role_id,
                        role_update.name,
                    )
                    return Error(
                        detail="Role name already exists",
                        code=status.HTTP_400_BAD_REQUEST,
                    )

            existing_role.name = role_update.name
            existing_role.description = role_update.description

            permissions = await uow.role_repository.get_permissions_by_codes(
                role_update.permissions
            )
            existing_role.permissions = permissions

            await uow.commit()
            result = await uow.role_repository.get_role_by_id(role_id)

        logger.info("Role updated successfully (id=%s)", role_id)
        return result

    async def delete_role(self, role_id: UUID4) -> Message | Error:
        logger.info("Deleting role (id=%s)", role_id)

        async with self._unit_of_work as uow:
            role_to_delete = await uow.role_repository.get_role_by_id(role_id)
            if not role_to_delete:
                logger.warning("Role deletion failed: not found (id=%s)", role_id)
                return Error(detail="Role not found", code=status.HTTP_404_NOT_FOUND)

            # Check if any users are assigned to this role
            user_count = await uow.user_repository.count_users_by_role_id(role_id)
            if user_count > 0:
                logger.warning(
                    "Role deletion failed: users are assigned (id=%s, user_count=%s)",
                    role_id,
                    user_count,
                )
                return Error(
                    detail=f"Cannot delete role. {user_count} user(s) are assigned to this role",
                    code=status.HTTP_400_BAD_REQUEST,
                )

            await uow.role_repository.delete_role(role_to_delete)
            await uow.commit()

        logger.info("Role deleted successfully (id=%s)", role_id)
        return Message(detail="Role deleted successfully")

    async def update_role_status(
        self, role_id: UUID4, status_update: RoleStatusUpdate
    ) -> Role | Error:
        logger.info(
            "Updating role status (id=%s, is_active=%s)",
            role_id,
            status_update.is_active,
        )

        async with self._unit_of_work as uow:
            role = await uow.role_repository.get_role_by_id(role_id)
            if not role:
                logger.warning("Role status update failed: not found (id=%s)", role_id)
                return Error(detail="Role not found", code=status.HTTP_404_NOT_FOUND)

            role.is_active = status_update.is_active
            await uow.commit()
            updated_role = await uow.role_repository.get_role_by_id(role_id)

        logger.info("Role status updated successfully (id=%s)", role_id)
        return updated_role

    async def assign_permissions(
        self, role_id: UUID4, request: AssignPermissionsRequest
    ) -> Role | Error:
        logger.info("Assigning permissions to role (id=%s)", role_id)

        async with self._unit_of_work as uow:
            role = await uow.role_repository.get_role_by_id(role_id)
            if not role:
                logger.warning("Role not found (id=%s)", role_id)
                return Error(detail="Role not found", code=status.HTTP_404_NOT_FOUND)

            await uow.role_repository.assign_permissions_to_role(
                role, request.permission_ids
            )
            await uow.commit()
            role = await uow.role_repository.get_role_by_id(role_id)

        logger.info("Permissions assigned successfully (role_id=%s)", role_id)
        return role
