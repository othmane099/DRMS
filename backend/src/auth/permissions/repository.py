from typing import Protocol

from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import Permission


class PermissionRepository(Protocol):
    async def get_all_permissions(self) -> list[Permission]: ...

    async def get_permissions_by_role_id(self, role_id: UUID4) -> list[Permission]: ...


class PermissionRepositoryImpl(PermissionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_permissions(self) -> list[Permission]:
        result = await self.session.execute(
            select(Permission).where(Permission.is_active.is_(True))
        )
        return list(result.scalars().unique().all())

    async def get_permissions_by_role_id(self, role_id: UUID4) -> list[Permission]:
        from auth.models import Role, role_permissions

        result = await self.session.execute(
            select(Permission)
            .join(role_permissions)
            .join(Role)
            .where(Role.id == role_id)
            .where(Permission.is_active.is_(True))
        )
        return list(result.scalars().unique().all())
