import logging
import re
from datetime import datetime
from typing import Protocol
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from pydantic import UUID4
from starlette import status

from auth.models import User
from auth.users.schemas import (
    BulkActionResponse,
    BulkUserAction,
    PaginatedUserResponse,
    PermissionBasicResponse,
    UserCreate,
    UserPermissionsResponse,
    UserPermissionsUpdate,
    UserResponse,
    UserRoleUpdate,
    UserStatus,
    UserStatusUpdate,
    UserUpdate,
)
from schemas import Error, Message
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._ -]+$")


class UserService(Protocol):
    async def get_all_users_paginated(
        self,
        page: int,
        page_size: int,
        role_id: UUID | None = None,
        search: str | None = None,
        active: UserStatus | None = None,
    ) -> PaginatedUserResponse | Error: ...

    async def get_all_users(self, uow: UnitOfWork) -> list[User]: ...

    async def get_all_users_except_superuser(self, uow: UnitOfWork) -> list[User]: ...

    async def get_users_for_assignment(self, current_user_id: UUID) -> list[User]: ...

    async def count_users(self) -> int: ...

    async def count_users_by_role_id(self, role_id: UUID4) -> int: ...

    async def get_user_by_id(self, user_id: UUID) -> User | Error: ...

    async def get_user_by_username(
        self, username: str, uow: UnitOfWork | None = None, exclude_deleted: bool = True
    ) -> User | Error: ...

    async def get_user_by_email(
        self, email: str, exclude_deleted: bool = True
    ) -> User | Error: ...

    async def get_user_by_phone(
        self, phone: str, exclude_deleted: bool = True
    ) -> User | Error: ...

    async def create_user(self, user_create: UserCreate) -> User | Error: ...

    async def update_user(
        self, user_id: UUID4, user_update: UserUpdate
    ) -> User | Error: ...

    async def delete_user(self, user_id: UUID4) -> Message | Error: ...

    async def update_user_status(
        self, user_id: UUID4, status_update: UserStatusUpdate
    ) -> User | Error: ...

    async def update_user_role(
        self, user_id: UUID4, role_update: UserRoleUpdate
    ) -> User | Error: ...

    async def bulk_action(
        self, bulk_action: BulkUserAction
    ) -> BulkActionResponse | Error: ...

    async def get_user_permissions(
        self, user_id: UUID
    ) -> UserPermissionsResponse | Error: ...

    async def update_user_permissions(
        self, user_id: UUID, permissions_update: UserPermissionsUpdate
    ) -> UserPermissionsResponse | Error: ...


class UserServiceImpl(UserService):
    @inject
    def __init__(self, unit_of_work: UnitOfWork = Provide["unit_of_work"]):
        self._unit_of_work = unit_of_work

    async def get_all_users_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        role_id: UUID | None = None,
        search: str | None = None,
        active: UserStatus | None = None,
    ) -> PaginatedUserResponse | Error:
        logger.debug(
            "Fetching users (page=%s, page_size=%s, role_id=%s, search=%s, active=%s)",
            page,
            page_size,
            role_id,
            search,
            active,
        )

        active_bool: bool | None = None
        if active is not None:
            active_bool = active == UserStatus.active

        skip = (page - 1) * page_size
        limit = page_size

        async with self._unit_of_work as uow:
            users = await uow.user_repository.get_all_users_paginated(
                skip=skip,
                limit=limit,
                role_id=role_id,
                search=search,
                active=active_bool,
            )
            total_rows = await uow.user_repository.count_users(
                role_id=role_id, search=search, active=active_bool
            )

        total_pages = (total_rows + page_size - 1) // page_size

        logger.info(
            "Users fetched (page=%s, page_size=%s, total_rows=%s, total_pages=%s)",
            page,
            page_size,
            total_rows,
            total_pages,
        )
        return PaginatedUserResponse(
            data=[UserResponse.model_validate(user) for user in users],
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    async def get_all_users(self, uow: UnitOfWork) -> list[User]:
        logger.debug("Fetching all users (shared UoW)")
        return await uow.user_repository.get_all_users()

    async def get_all_users_except_superuser(self, uow: UnitOfWork) -> list[User]:
        logger.debug("Fetching all users except superuser")
        return await uow.user_repository.get_all_user_except_superuser()

    async def get_users_for_assignment(self, current_user_id: UUID) -> list[User]:
        logger.debug(
            "Fetching users for assignment (excluding current user and superusers)"
        )

        async with self._unit_of_work as uow:
            users = await uow.user_repository.get_users_for_assignment(current_user_id)

        logger.debug("Users for assignment fetched (count=%s)", len(users))
        return users

    async def count_users(self) -> int:
        logger.debug("Counting users")

        async with self._unit_of_work as uow:
            count = await uow.user_repository.count_users()

        logger.debug("User count resolved (count=%s)", count)
        return count

    async def count_users_by_role_id(self, role_id: UUID4) -> int:
        logger.debug("Counting users for role (role_id=%s)", role_id)

        async with self._unit_of_work as uow:
            count = await uow.user_repository.count_users_by_role_id(role_id)

        logger.debug(
            "User count for role resolved (role_id=%s, count=%s)", role_id, count
        )
        return count

    async def get_user_by_id(
        self, user_id: UUID, uow: UnitOfWork | None = None
    ) -> User | Error:
        logger.debug("Fetching user by id=%s", user_id)

        if uow is None:
            async with self._unit_of_work as uow:
                user = await uow.user_repository.get_user_by_id(user_id)
        else:
            user = await uow.user_repository.get_user_by_id(user_id)

        if not user:
            logger.warning("User not found (id=%s)", user_id)
            return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

        logger.debug("User found (id=%s)", user_id)
        return user

    async def get_user_by_username(
        self, username: str, uow: UnitOfWork | None = None, exclude_deleted: bool = True
    ) -> User | Error:
        logger.debug("Fetching user by username=%s", username)

        if uow is None:
            async with self._unit_of_work as uow:
                user = await uow.user_repository.get_user_by_username(
                    username, exclude_deleted=exclude_deleted
                )
        else:
            user = await uow.user_repository.get_user_by_username(
                username, exclude_deleted=exclude_deleted
            )

        if not user:
            logger.warning("User not found (username=%s)", username)
            return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

        logger.debug("User found (username=%s)", username)
        return user

    async def create_user(self, user_create: UserCreate) -> User | Error:
        logger.info("Creating user (username=%s)", user_create.username)

        username_error = self._validate_username_format(user_create.username)
        if username_error:
            logger.warning(
                "User creation rejected: invalid username characters (username=%s)",
                user_create.username,
            )
            return username_error

        normalized_username = user_create.username.lower()
        normalized_create = user_create.model_copy(
            update={"username": normalized_username}
        )
        hashed_password = pbkdf2_sha256.hash(normalized_create.password)
        user_create_with_hash = normalized_create.model_copy(
            update={"password": hashed_password}
        )

        async with self._unit_of_work as uow:
            existing_user = await self.get_user_by_username(
                normalized_username, uow, exclude_deleted=False
            )
            if not isinstance(existing_user, Error):
                logger.warning(
                    "User creation rejected: username already exists (username=%s)",
                    normalized_username,
                )
                return Error(
                    detail="Username already exists", code=status.HTTP_400_BAD_REQUEST
                )

            if user_create.email:
                if await uow.user_repository.get_user_by_email(
                    user_create.email, exclude_deleted=False
                ):
                    logger.warning(
                        "User creation rejected: email already exists (email=%s)",
                        user_create.email,
                    )
                    return Error(
                        detail="Email already exists", code=status.HTTP_400_BAD_REQUEST
                    )

            if user_create.phone:
                if await uow.user_repository.get_user_by_phone(
                    user_create.phone, exclude_deleted=False
                ):
                    logger.warning(
                        "User creation rejected: phone already exists (phone=%s)",
                        user_create.phone,
                    )
                    return Error(
                        detail="Phone already exists", code=status.HTTP_400_BAD_REQUEST
                    )

            instance = await uow.user_repository.create_user(user_create_with_hash)
            await uow.commit()
            created_user = await uow.user_repository.get_user_by_id(instance.id)

        logger.info(
            "User created successfully (id=%s, username=%s)",
            created_user.id,
            created_user.username,
        )
        return created_user

    async def update_user(
        self, user_id: UUID4, user_update: UserUpdate
    ) -> User | Error:
        logger.info("Updating user (id=%s)", user_id)

        async with self._unit_of_work as uow:
            existing_user = await self.get_user_by_id(user_id, uow)
            if isinstance(existing_user, Error):
                logger.warning("User update failed: not found (id=%s)", user_id)
                return existing_user

            normalized_username = user_update.username.lower()
            if existing_user.username != normalized_username:
                username_error = self._validate_username_format(user_update.username)
                if username_error:
                    logger.warning(
                        "User update rejected: invalid username characters (username=%s)",
                        user_update.username,
                    )
                    return username_error

                conflict = await self.get_user_by_username(
                    normalized_username, uow, exclude_deleted=False
                )
                if not isinstance(conflict, Error):
                    logger.warning(
                        "User update rejected: username conflict (id=%s, username=%s)",
                        user_id,
                        user_update.username,
                    )
                    return Error(
                        detail="Username already exists",
                        code=status.HTTP_400_BAD_REQUEST,
                    )

            if user_update.email and existing_user.email != user_update.email:
                if await uow.user_repository.get_user_by_email(
                    user_update.email, exclude_deleted=False
                ):
                    logger.warning(
                        "User update rejected: email conflict (id=%s, email=%s)",
                        user_id,
                        user_update.email,
                    )
                    return Error(
                        detail="Email already exists", code=status.HTTP_400_BAD_REQUEST
                    )

            if user_update.phone and existing_user.phone != user_update.phone:
                if await uow.user_repository.get_user_by_phone(
                    user_update.phone, exclude_deleted=False
                ):
                    logger.warning(
                        "User update rejected: phone conflict (id=%s, phone=%s)",
                        user_id,
                        user_update.phone,
                    )
                    return Error(
                        detail="Phone already exists", code=status.HTTP_400_BAD_REQUEST
                    )

            user_to_update = await uow.user_repository.get_user_by_id(user_id)
            user_to_update.first_name = user_update.first_name
            user_to_update.last_name = user_update.last_name
            user_to_update.email = user_update.email
            user_to_update.phone = user_update.phone
            user_to_update.username = normalized_username
            user_to_update.is_active = user_update.is_active
            user_to_update.role_id = user_update.role_id
            await uow.commit()
            updated_user = await uow.user_repository.get_user_by_id(UUID(str(user_id)))
        logger.info("User updated successfully (id=%s)", user_id)
        return updated_user

    async def delete_user(self, user_id: UUID4) -> Message | Error:
        logger.info("Deleting user (id=%s)", user_id)

        async with self._unit_of_work as uow:
            user_to_delete = await uow.user_repository.get_user_by_id(user_id)
            if not user_to_delete:
                logger.warning("User deletion failed: not found (id=%s)", user_id)
                return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)
            user_to_delete.deleted_at = datetime.now()  # type: ignore
            await uow.commit()

        logger.info("User deleted successfully (id=%s)", user_id)
        return Message(detail="User deleted successfully")

    def _validate_username_format(self, username: str) -> Error | None:
        if username == "":
            return Error(
                detail="Username cannot be empty",
                code=status.HTTP_400_BAD_REQUEST,
            )
        if not username.isascii():
            return Error(
                detail="Username contains invalid characters",
                code=status.HTTP_400_BAD_REQUEST,
            )
        if username.strip() != username:
            return Error(
                detail="Username cannot have leading or trailing whitespace",
                code=status.HTTP_400_BAD_REQUEST,
            )
        if not _USERNAME_PATTERN.fullmatch(username):
            return Error(
                detail="Username contains invalid characters",
                code=status.HTTP_400_BAD_REQUEST,
            )
        return None

    async def update_user_status(
        self, user_id: UUID4, status_update: UserStatusUpdate
    ) -> User | Error:
        logger.info(
            "Updating user status (id=%s, is_active=%s)",
            user_id,
            status_update.is_active,
        )

        async with self._unit_of_work as uow:
            user = await uow.user_repository.get_user_by_id(user_id)
            if not user:
                logger.warning("User status update failed: not found (id=%s)", user_id)
                return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

            user.is_active = status_update.is_active
            await uow.commit()
            updated_user = await uow.user_repository.get_user_by_id(user_id)

        logger.info("User status updated successfully (id=%s)", user_id)
        return updated_user

    async def update_user_role(
        self, user_id: UUID4, role_update: UserRoleUpdate
    ) -> User | Error:
        logger.info(
            "Updating user role (id=%s, role_id=%s)", user_id, role_update.role_id
        )

        async with self._unit_of_work as uow:
            user = await uow.user_repository.get_user_by_id(user_id)
            if not user:
                logger.warning("User role update failed: not found (id=%s)", user_id)
                return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

            new_role_id = None
            if role_update.role_id:
                new_role_id = role_update.role_id
                role = await uow.role_repository.get_role_by_id(role_update.role_id)
                if not role:
                    logger.warning(
                        "User role update failed: role not found (role_id=%s)",
                        role_update.role_id,
                    )
                    return Error(
                        detail="Role not found", code=status.HTTP_404_NOT_FOUND
                    )

            user.role_id = new_role_id
            await uow.commit()
            updated_user = await uow.user_repository.get_user_by_id(user_id)

        logger.info("User role updated successfully (id=%s)", user_id)
        return updated_user

    async def bulk_action(
        self, bulk_action: BulkUserAction
    ) -> BulkActionResponse | Error:
        logger.info(
            "Performing bulk action (action=%s, user_count=%s)",
            bulk_action.action,
            len(bulk_action.user_ids),
        )

        valid_actions = ["assign_role", "activate", "deactivate", "delete"]
        if bulk_action.action not in valid_actions:
            return Error(
                detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}",
                code=status.HTTP_400_BAD_REQUEST,
            )

        success_count = 0
        failure_count = 0
        details: list[str] = []

        async with self._unit_of_work as uow:
            for user_id in bulk_action.user_ids:
                user = await uow.user_repository.get_user_by_id(user_id)
                if not user:
                    failure_count += 1
                    details.append(f"User {user_id} not found")
                    continue

                if bulk_action.action == "assign_role":
                    if (
                        not bulk_action.parameters
                        or "role_id" not in bulk_action.parameters
                    ):
                        failure_count += 1
                        details.append(f"User {user_id}: role_id parameter required")
                        continue
                    role_id = bulk_action.parameters["role_id"]
                    role = await uow.role_repository.get_role_by_id(UUID(role_id))
                    if not role:
                        failure_count += 1
                        details.append(f"User {user_id}: role not found")
                        continue
                    user.role_id = UUID(role_id)
                    success_count += 1

                elif bulk_action.action == "activate":
                    user.is_active = True
                    success_count += 1

                elif bulk_action.action == "deactivate":
                    user.is_active = False
                    success_count += 1

                elif bulk_action.action == "delete":
                    user.deleted_at = datetime.now()
                    success_count += 1

            await uow.commit()

        logger.info(
            "Bulk action completed (action=%s, success=%s, failure=%s)",
            bulk_action.action,
            success_count,
            failure_count,
        )
        return BulkActionResponse(
            success_count=success_count,
            failure_count=failure_count,
            details=details if details else None,
        )

    async def get_user_permissions(
        self, user_id: UUID
    ) -> UserPermissionsResponse | Error:
        logger.debug("Fetching user permissions (id=%s)", user_id)

        async with self._unit_of_work as uow:
            user = await uow.user_repository.get_user_with_permissions(user_id)
            if not user:
                logger.warning("User not found (id=%s)", user_id)
                return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

            role_permissions = []
            if user.role and user.role.permissions:
                role_permissions = [
                    PermissionBasicResponse.model_validate(p)
                    for p in user.role.permissions
                ]

            custom_permissions = [
                PermissionBasicResponse.model_validate(p)
                for p in user.custom_permissions
            ]

        logger.debug("User permissions fetched (id=%s)", user_id)
        return UserPermissionsResponse(
            id=user.id,
            username=user.username,
            role_permissions=role_permissions,
            custom_permissions=custom_permissions,
        )

    async def update_user_permissions(
        self, user_id: UUID, permissions_update: UserPermissionsUpdate
    ) -> UserPermissionsResponse | Error:
        logger.info("Updating user permissions (id=%s)", user_id)

        async with self._unit_of_work as uow:
            user = await uow.user_repository.get_user_with_permissions(user_id)
            if not user:
                logger.warning("User not found (id=%s)", user_id)
                return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

            if permissions_update.permissions:
                all_permissions = await uow.user_repository.get_permissions_by_codes(
                    permissions_update.permissions
                )
                permission_ids = [p.id for p in all_permissions]
                await uow.user_repository.assign_permissions_to_user(
                    user, permission_ids
                )
            else:
                await uow.user_repository.assign_permissions_to_user(user, [])

            await uow.commit()
            updated_user = await uow.user_repository.get_user_with_permissions(user_id)

        role_permissions = []
        if updated_user.role and updated_user.role.permissions:
            role_permissions = [
                PermissionBasicResponse.model_validate(p)
                for p in updated_user.role.permissions
            ]

        custom_permissions = [
            PermissionBasicResponse.model_validate(p)
            for p in updated_user.custom_permissions
        ]

        logger.info("User permissions updated successfully (id=%s)", user_id)
        return UserPermissionsResponse(
            id=updated_user.id,
            username=updated_user.username,
            role_permissions=role_permissions,
            custom_permissions=custom_permissions,
        )
