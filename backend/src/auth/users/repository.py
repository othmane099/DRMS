from typing import Protocol

from pydantic import UUID4
from sqlalchemy import func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth.models import Permission, Role, User
from auth.users.schemas import UserCreate


class UserRepository(Protocol):
    async def get_all_users_paginated(
        self,
        skip: int,
        limit: int,
        role_id: UUID4 | None = None,
        search: str | None = None,
        active: bool | None = None,
    ) -> list[User]: ...

    async def get_users_for_assignment(self, current_user_id: UUID4) -> list[User]: ...

    async def count_users(
        self,
        role_id: UUID4 | None = None,
        search: str | None = None,
        active: bool | None = None,
    ) -> int: ...

    async def count_users_by_role_id(self, role_id: UUID4) -> int: ...

    async def get_user_by_id(self, user_id: UUID4) -> User | None: ...

    async def get_user_with_permissions(self, user_id: UUID4) -> User | None: ...

    async def assign_permissions_to_user(
        self, user: User, permission_ids: list[UUID4]
    ) -> None: ...

    async def get_permissions_by_codes(self, codes: list[str]) -> list[Permission]: ...

    async def get_user_by_username(
        self, username: str, exclude_deleted: bool = True
    ) -> User | None: ...

    async def get_user_by_email(
        self, email: str, exclude_deleted: bool = True
    ) -> User | None: ...

    async def get_user_by_phone(
        self, phone: str, exclude_deleted: bool = True
    ) -> User | None: ...

    async def create_user(self, user_create: UserCreate) -> User | None: ...

    async def get_user_by_telegram_chat_id(self, chat_id: int) -> User | None: ...

    async def link_telegram(self, user_id: UUID4, chat_id: int) -> None: ...

    async def unlink_telegram(self, chat_id: int) -> None: ...


class UserRepositoryImpl(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_users_paginated(
        self,
        skip: int = 0,
        limit: int = 10,
        role_id: UUID4 | None = None,
        search: str | None = None,
        active: bool | None = None,
    ) -> list[User]:
        query = (
            select(User)
            .where(User.deleted_at.is_(None))
            .where(User.is_superuser.is_(False))
            .options(selectinload(User.role).selectinload(Role.permissions))
            .options(selectinload(User.custom_permissions))
        )

        if role_id:
            query = query.where(User.role_id == role_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.username.ilike(search_pattern),
                )
            )

        if active is not None:
            query = query.where(User.is_active == active)

        query = query.order_by(User.username).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def get_users_for_assignment(self, current_user_id: UUID4) -> list[User]:
        query = (
            select(User)
            .where(User.deleted_at.is_(None))
            .where(User.is_superuser.is_(False))
            .where(User.id != current_user_id)
            .where(User.is_active.is_(True))
            .options(selectinload(User.role))
            .order_by(User.first_name, User.last_name)
        )
        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def count_users(
        self,
        role_id: UUID4 | None = None,
        search: str | None = None,
        active: bool | None = None,
    ) -> int:
        query = (
            select(func.count(User.id))
            .where(User.deleted_at.is_(None))
            .where(User.is_superuser.is_(False))
        )

        if role_id:
            query = query.where(User.role_id == role_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.username.ilike(search_pattern),
                )
            )

        if active is not None:
            query = query.where(User.is_active == active)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def count_users_by_role_id(self, role_id: UUID4) -> int:
        result = await self.session.execute(
            select(func.count(User.id))
            .where(User.role_id == role_id)
            .where(User.is_active.is_(True))
            .where(User.is_superuser.is_(False))
        )
        return result.scalar_one()

    async def get_user_by_id(self, user_id: UUID4) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .where(User.deleted_at.is_(None))
            .where(User.is_superuser.is_(False))
            .options(
                selectinload(User.role).selectinload(Role.permissions),
                selectinload(User.custom_permissions),
            )
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(
        self, username: str, exclude_deleted: bool = True
    ) -> User | None:
        query = (
            select(User)
            .where(User.username == username)
            .options(
                selectinload(User.role).selectinload(Role.permissions),
                selectinload(User.custom_permissions),
            )
        )
        if exclude_deleted:
            query = query.where(User.deleted_at.is_(None))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_email(
        self, email: str, exclude_deleted: bool = True
    ) -> User | None:
        query = select(User).where(User.email == email).options(selectinload(User.role))
        if exclude_deleted:
            query = query.where(User.deleted_at.is_(None))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_phone(
        self, phone: str, exclude_deleted: bool = True
    ) -> User | None:
        query = select(User).where(User.phone == phone).options(selectinload(User.role))
        if exclude_deleted:
            query = query.where(User.deleted_at.is_(None))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_user(self, user_create: UserCreate) -> User | None:
        stmt = insert(User).values(**user_create.model_dump()).returning(User)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_with_permissions(self, user_id: UUID4) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .where(User.deleted_at.is_(None))
            .where(User.is_superuser.is_(False))
            .options(
                selectinload(User.role).selectinload(Role.permissions),
                selectinload(User.custom_permissions),
            )
        )
        return result.scalar_one_or_none()

    async def assign_permissions_to_user(
        self, user: User, permission_ids: list[UUID4]
    ) -> None:
        result = await self.session.execute(
            select(Permission).where(Permission.id.in_(permission_ids))
        )
        permissions = list(result.scalars().all())
        user.custom_permissions = permissions

    async def get_permissions_by_codes(self, codes: list[str]) -> list[Permission]:
        result = await self.session.execute(
            select(Permission)
            .where(Permission.code.in_(codes))
            .where(Permission.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def get_user_by_telegram_chat_id(self, chat_id: int) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.telegram_chat_id == chat_id)
            .where(User.deleted_at.is_(None))
            .options(
                selectinload(User.role).selectinload(Role.permissions),
                selectinload(User.custom_permissions),
            )
        )
        return result.scalar_one_or_none()

    async def link_telegram(self, user_id: UUID4, chat_id: int) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(telegram_chat_id=chat_id)
        )

    async def unlink_telegram(self, chat_id: int) -> None:
        await self.session.execute(
            update(User)
            .where(User.telegram_chat_id == chat_id)
            .values(telegram_chat_id=None)
        )
