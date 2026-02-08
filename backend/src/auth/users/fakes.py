from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from passlib.handlers.pbkdf2 import pbkdf2_sha256
from pydantic import UUID4
from starlette import status

from auth.models import Permission, User
from auth.users.repository import UserRepository
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
from auth.users.service import _USERNAME_PATTERN, UserService
from schemas import Error, Message
from unit_of_work.uow import UnitOfWork


class FakeUserRepository(UserRepository):
    def __init__(self, session: Any = None):
        self.session = session
        self.users: dict[UUID, User] = {}
        self.permissions: dict[UUID, Permission] = {}

    async def get_all_users_paginated(
        self,
        skip: int = 0,
        limit: int = 10,
        role_id: UUID4 | None = None,
        search: str | None = None,
        active: bool | None = None,
    ) -> list[User]:
        active_users = [
            u
            for u in self.users.values()
            if u.deleted_at is None and not u.is_superuser
        ]

        if role_id:
            active_users = [u for u in active_users if u.role_id == role_id]

        if search:
            search_lower = search.lower()
            active_users = [
                u
                for u in active_users
                if (u.first_name and search_lower in u.first_name.lower())
                or (u.last_name and search_lower in u.last_name.lower())
                or (u.email and search_lower in u.email.lower())
                or (u.username and search_lower in u.username.lower())
            ]

        if active is not None:
            active_users = [u for u in active_users if u.is_active == active]

        return sorted(active_users, key=lambda x: x.username)[skip : skip + limit]

    async def get_all_users(self) -> list[User]:
        return [u for u in self.users.values() if u.deleted_at is None]

    async def get_all_user_except_superuser(self) -> list[User]:
        return [
            u
            for u in self.users.values()
            if u.deleted_at is None and not u.is_superuser
        ]

    async def get_user_by_id(self, user_id: UUID4) -> User | None:
        user = self.users.get(user_id)
        if user and user.deleted_at is None and not user.is_superuser:
            return user
        return None

    async def get_user_by_username(
        self, username: str, exclude_deleted: bool = True
    ) -> User | None:
        for user in self.users.values():
            if user.username == username:
                if not exclude_deleted or user.deleted_at is None:
                    return user
        return None

    async def get_user_by_email(
        self, email: str, exclude_deleted: bool = True
    ) -> User | None:
        for user in self.users.values():
            if user.email == email:
                if not exclude_deleted or user.deleted_at is None:
                    return user
        return None

    async def get_user_by_phone(
        self, phone: str, exclude_deleted: bool = True
    ) -> User | None:
        for user in self.users.values():
            if user.phone == phone:
                if not exclude_deleted or user.deleted_at is None:
                    return user
        return None

    async def create_user(self, user_create: UserCreate) -> User | None:
        user = User(
            id=uuid4(),
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            email=user_create.email,
            phone=user_create.phone,
            username=user_create.username,
            password=user_create.password,
            is_active=user_create.is_active,
            role_id=user_create.role_id,
            is_superuser=False,
            created_at=datetime.now(),
        )
        self.users[UUID(str(user.id))] = user
        return user

    async def count_users(
        self,
        role_id: UUID4 | None = None,
        search: str | None = None,
        active: bool | None = None,
    ) -> int:
        active_users = [
            u
            for u in self.users.values()
            if u.deleted_at is None and not u.is_superuser
        ]

        if role_id:
            active_users = [u for u in active_users if u.role_id == role_id]

        if search:
            search_lower = search.lower()
            active_users = [
                u
                for u in active_users
                if (u.first_name and search_lower in u.first_name.lower())
                or (u.last_name and search_lower in u.last_name.lower())
                or (u.email and search_lower in u.email.lower())
                or (u.username and search_lower in u.username.lower())
            ]

        if active is not None:
            active_users = [u for u in active_users if u.is_active == active]

        return len(active_users)

    async def count_users_by_role_id(self, role_id: UUID4) -> int:
        return len(
            [
                u
                for u in self.users.values()
                if u.role_id == role_id and u.is_active and not u.is_superuser
            ]
        )

    async def get_user_with_permissions(self, user_id: UUID4) -> User | None:
        user = self.users.get(user_id)
        if user and user.deleted_at is None and not user.is_superuser:
            return user
        return None

    async def assign_permissions_to_user(
        self, user: User, permission_ids: list[UUID4]
    ) -> None:
        permissions = [
            self.permissions[pid] for pid in permission_ids if pid in self.permissions
        ]
        user.custom_permissions = permissions

    async def get_permissions_by_codes(self, codes: list[str]) -> list[Permission]:
        return [p for p in self.permissions.values() if p.code in codes]


class FakeUserService(UserService):
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}
        self.permissions: dict[UUID, Permission] = {}

    async def get_all_users_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        role_id: UUID | None = None,
        search: str | None = None,
        active: UserStatus | None = None,
    ) -> PaginatedUserResponse | Error:
        if page < 1:
            return Error(
                detail="Page must be greater than or equal to 1",
                code=status.HTTP_400_BAD_REQUEST,
            )
        if page_size < 1:
            return Error(
                detail="Page size must be greater than or equal to 1",
                code=status.HTTP_400_BAD_REQUEST,
            )

        # Convert UserStatus enum to boolean for filtering
        active_bool: bool | None = None
        if active is not None:
            active_bool = active == UserStatus.active

        skip = (page - 1) * page_size

        active_users = [
            u
            for u in self.users.values()
            if u.deleted_at is None and not u.is_superuser
        ]

        if role_id:
            active_users = [u for u in active_users if u.role_id == role_id]

        if search:
            search_lower = search.lower()
            active_users = [
                u
                for u in active_users
                if (u.first_name and search_lower in u.first_name.lower())
                or (u.last_name and search_lower in u.last_name.lower())
                or (u.email and search_lower in u.email.lower())
                or (u.username and search_lower in u.username.lower())
            ]

        if active_bool is not None:
            active_users = [u for u in active_users if u.is_active == active_bool]

        sorted_users = sorted(active_users, key=lambda x: x.username)
        paginated_users = sorted_users[skip : skip + page_size]

        total_rows = len(active_users)
        total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 0

        return PaginatedUserResponse(
            data=[UserResponse.model_validate(user) for user in paginated_users],
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    async def get_all_users(self, uow: UnitOfWork) -> list[User]:
        return [u for u in self.users.values() if u.deleted_at is None]

    async def get_all_users_except_superuser(self, uow: UnitOfWork) -> list[User]:
        return [
            u
            for u in self.users.values()
            if u.deleted_at is None and not u.is_superuser
        ]

    async def count_users(self) -> int:
        return len(
            [
                u
                for u in self.users.values()
                if u.deleted_at is None and not u.is_superuser
            ]
        )

    async def count_users_by_role_id(self, role_id: UUID4) -> int:
        return len(
            [
                u
                for u in self.users.values()
                if u.role_id == role_id and u.is_active and not u.is_superuser
            ]
        )

    async def get_user_by_id(self, user_id: UUID) -> User | Error:
        user = self.users.get(user_id)
        if user and user.deleted_at is None and not user.is_superuser:
            return user
        return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

    async def get_user_by_username(
        self, username: str, uow=None, exclude_deleted: bool = True
    ) -> User | Error:
        for user in self.users.values():
            if user.username == username:
                if not exclude_deleted or user.deleted_at is None:
                    return user
        return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

    async def get_user_by_email(
        self, email: str, exclude_deleted: bool = True
    ) -> User | Error:
        for user in self.users.values():
            if user.email == email:
                if not exclude_deleted or user.deleted_at is None:
                    return user
        return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

    async def get_user_by_phone(
        self, phone: str, exclude_deleted: bool = True
    ) -> User | Error:
        for user in self.users.values():
            if user.phone == phone:
                if not exclude_deleted or user.deleted_at is None:
                    return user
        return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

    async def create_user(self, user_create: UserCreate) -> User | Error:
        if not user_create.username or user_create.username.strip() == "":
            return Error(
                detail="Username cannot be empty",
                code=status.HTTP_400_BAD_REQUEST,
            )

        if not _USERNAME_PATTERN.match(user_create.username):
            return Error(
                detail="Username contains invalid characters",
                code=status.HTTP_400_BAD_REQUEST,
            )

        username_lower = user_create.username.lower()
        existing_username = await self.get_user_by_username(
            username_lower, exclude_deleted=False
        )
        if not isinstance(existing_username, Error):
            return Error(
                detail="Username already exists",
                code=status.HTTP_400_BAD_REQUEST,
            )

        if user_create.email:
            existing_email = await self.get_user_by_email(
                user_create.email, exclude_deleted=False
            )
            if not isinstance(existing_email, Error):
                return Error(
                    detail="Email already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

        if user_create.phone:
            existing_phone = await self.get_user_by_phone(
                user_create.phone, exclude_deleted=False
            )
            if not isinstance(existing_phone, Error):
                return Error(
                    detail="Phone already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

        hashed_password = pbkdf2_sha256.hash(user_create.password)

        user = User(
            id=uuid4(),
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            email=user_create.email,
            phone=user_create.phone,
            username=username_lower,
            password=hashed_password,
            is_active=user_create.is_active,
            role_id=user_create.role_id,
            is_superuser=False,
            created_at=datetime.now(),
        )
        self.users[user.id] = user
        return user

    async def update_user(
        self, user_id: UUID4, user_update: UserUpdate
    ) -> User | Error:
        existing_user = await self.get_user_by_id(user_id)
        if isinstance(existing_user, Error):
            return existing_user

        if user_update.username:
            username_lower = user_update.username.lower()
            if existing_user.username != username_lower:
                conflict = await self.get_user_by_username(
                    username_lower, exclude_deleted=False
                )
                if not isinstance(conflict, Error):
                    return Error(
                        detail="Username already exists",
                        code=status.HTTP_400_BAD_REQUEST,
                    )

        if user_update.email and existing_user.email != user_update.email:
            conflict = await self.get_user_by_email(
                user_update.email, exclude_deleted=False
            )
            if not isinstance(conflict, Error):
                return Error(
                    detail="Email already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

        if user_update.phone and existing_user.phone != user_update.phone:
            conflict = await self.get_user_by_phone(
                user_update.phone, exclude_deleted=False
            )
            if not isinstance(conflict, Error):
                return Error(
                    detail="Phone already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

        user = self.users[user_id]
        user.first_name = user_update.first_name
        user.last_name = user_update.last_name
        user.email = user_update.email
        user.phone = user_update.phone
        if user_update.username:
            user.username = user_update.username.lower()
        user.is_active = user_update.is_active
        if user_update.role_id:
            user.role_id = user_update.role_id
        return user

    async def delete_user(self, user_id: UUID4) -> Message | Error:
        user = self.users.get(user_id)
        if not user or user.deleted_at is not None or user.is_superuser:
            return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

        user.deleted_at = datetime.now()
        return Message(detail="User deleted successfully")

    async def update_user_status(
        self, user_id: UUID4, status_update: UserStatusUpdate
    ) -> User | Error:
        user = self.users.get(user_id)
        if not user or user.deleted_at is not None or user.is_superuser:
            return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

        user.is_active = status_update.is_active
        return user

    async def update_user_role(
        self, user_id: UUID4, role_update: UserRoleUpdate
    ) -> User | Error:
        user = self.users.get(user_id)
        if not user or user.deleted_at is not None or user.is_superuser:
            return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

        user.role_id = role_update.role_id
        return user

    async def bulk_action(
        self, bulk_action: BulkUserAction
    ) -> BulkActionResponse | Error:
        valid_actions = ["assign_role", "activate", "deactivate", "delete"]
        if bulk_action.action not in valid_actions:
            return Error(
                detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}",
                code=status.HTTP_400_BAD_REQUEST,
            )

        success_count = 0
        failure_count = 0
        details: list[str] = []

        for user_id in bulk_action.user_ids:
            user = self.users.get(user_id)
            if not user or user.deleted_at is not None or user.is_superuser:
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
                user.role_id = UUID(bulk_action.parameters["role_id"])
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

        return BulkActionResponse(
            success_count=success_count,
            failure_count=failure_count,
            details=details if details else None,
        )

    async def get_user_permissions(
        self, user_id: UUID
    ) -> UserPermissionsResponse | Error:
        user = self.users.get(user_id)
        if not user or user.deleted_at is not None or user.is_superuser:
            return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

        role_permissions: list[PermissionBasicResponse] = []
        custom_permissions = [
            PermissionBasicResponse.model_validate(p)
            for p in getattr(user, "custom_permissions", [])
        ]

        return UserPermissionsResponse(
            id=user.id,
            username=user.username,
            role_permissions=role_permissions,
            custom_permissions=custom_permissions,
        )

    async def update_user_permissions(
        self, user_id: UUID, permissions_update: UserPermissionsUpdate
    ) -> UserPermissionsResponse | Error:
        user = self.users.get(user_id)
        if not user or user.deleted_at is not None or user.is_superuser:
            return Error(detail="User not found", code=status.HTTP_404_NOT_FOUND)

        new_permissions = []
        for code in permissions_update.permissions:
            for p in self.permissions.values():
                if p.code == code:
                    new_permissions.append(p)
                    break

        user.custom_permissions = new_permissions

        return UserPermissionsResponse(
            id=user.id,
            username=user.username,
            role_permissions=[],
            custom_permissions=[
                PermissionBasicResponse.model_validate(p) for p in new_permissions
            ],
        )
