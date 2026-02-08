from typing import Protocol

from pydantic import UUID4
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth.models import Permission, Role
from auth.roles.schemas import RoleCreate


class RoleRepository(Protocol):
    async def get_all_roles(self, only_active: bool = False) -> list[Role]: ...

    async def get_role_by_id(
        self, role_id: UUID4, only_active: bool = False
    ) -> Role | None: ...

    async def get_role_by_name(
        self, name: str, only_active: bool = False
    ) -> Role | None: ...

    async def create_role(self, role_create: RoleCreate) -> Role | None: ...

    async def assign_permissions_to_role(
        self, role: Role, permission_ids: list[UUID4]
    ) -> None: ...

    async def get_permissions_by_codes(
        self, permission_codes: list[str]
    ) -> list[Permission]: ...

    async def delete_role(self, role: Role) -> None: ...


class RoleRepositoryImpl(RoleRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _handle_only_active_role(self, query, only_active: bool):
        if only_active:
            query = query.where(Role.is_active.is_(True))
        return query

    async def get_all_roles(self, only_active: bool = False) -> list[Role]:
        query = select(Role)
        query = self._handle_only_active_role(query, only_active)
        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def get_role_by_id(
        self, role_id: UUID4, only_active: bool = False
    ) -> Role | None:
        query = (
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.permissions))
        )
        query = self._handle_only_active_role(query, only_active)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_role_by_name(
        self, name: str, only_active: bool = False
    ) -> Role | None:
        query = select(Role).where(Role.name == name)
        query = self._handle_only_active_role(query, only_active)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_role(self, role_create: RoleCreate) -> Role | None:
        role_data = role_create.model_dump(exclude={"permissions"})
        stmt = insert(Role).values(**role_data).returning(Role)
        result = await self.session.execute(stmt)
        role = result.scalar_one_or_none()

        if role and role_create.permissions:
            permissions = await self.get_permissions_by_codes(role_create.permissions)
            # Refresh the role with permissions eagerly loaded to avoid lazy loading
            await self.session.refresh(role, ["permissions"])
            role.permissions = permissions

        return role

    async def assign_permissions_to_role(
        self, role: Role, permission_ids: list[UUID4]
    ) -> None:
        result = await self.session.execute(
            select(Permission).where(Permission.id.in_(permission_ids))
        )
        permissions = result.scalars().all()
        # Refresh the role with permissions eagerly loaded to avoid lazy loading
        await self.session.refresh(role, ["permissions"])
        role.permissions = permissions

    async def get_permissions_by_codes(
        self, permission_codes: list[str]
    ) -> list[Permission]:
        result = await self.session.execute(
            select(Permission)
            .where(Permission.code.in_(permission_codes))
            .where(Permission.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def delete_role(self, role: Role) -> None:
        await self.session.delete(role)
