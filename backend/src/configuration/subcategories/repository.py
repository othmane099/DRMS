from typing import Protocol

from pydantic import UUID4
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from configuration.models import Subcategory
from configuration.subcategories.schemas import SubcategoryCreate, SubcategoryUpdate


class SubcategoryRepository(Protocol):
    async def get_all_subcategories_paginated(
        self,
        skip: int,
        limit: int,
        search: str | None = None,
        category_id: UUID4 | None = None,
    ) -> list[Subcategory]: ...

    async def count_subcategories(
        self, search: str | None = None, category_id: UUID4 | None = None
    ) -> int: ...

    async def check_title_exists(self, title: str) -> bool: ...

    async def get_subcategory_by_id(
        self, subcategory_id: UUID4
    ) -> Subcategory | None: ...

    async def create_subcategory(
        self, subcategory_create: SubcategoryCreate
    ) -> Subcategory: ...

    async def update_subcategory(
        self, subcategory: Subcategory, subcategory_update: SubcategoryUpdate
    ) -> Subcategory: ...

    async def delete_subcategory(self, subcategory: Subcategory) -> None: ...


class SubcategoryRepositoryImpl(SubcategoryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_subcategories_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
        category_id: UUID4 | None = None,
    ) -> list[Subcategory]:
        query = select(Subcategory)

        if category_id:
            query = query.where(Subcategory.category_id == category_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(Subcategory.title.ilike(search_pattern))

        query = query.order_by(Subcategory.created_at).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_subcategories(
        self, search: str | None = None, category_id: UUID4 | None = None
    ) -> int:
        query = select(func.count(Subcategory.id))

        if category_id:
            query = query.where(Subcategory.category_id == category_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(Subcategory.title.ilike(search_pattern))

        result = await self.session.execute(query)
        return result.scalar_one()

    async def check_title_exists(self, title: str) -> bool:
        query = select(func.count(Subcategory.id)).where(
            func.lower(Subcategory.title) == title.lower()
        )
        result = await self.session.execute(query)
        return result.scalar_one() > 0

    async def get_subcategory_by_id(self, subcategory_id: UUID4) -> Subcategory | None:
        query = select(Subcategory).where(Subcategory.id == subcategory_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_subcategory(
        self, subcategory_create: SubcategoryCreate
    ) -> Subcategory:
        stmt = (
            insert(Subcategory)
            .values(**subcategory_create.model_dump())
            .returning(Subcategory)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_subcategory(
        self, subcategory: Subcategory, subcategory_update: SubcategoryUpdate
    ) -> Subcategory:
        subcategory.title = subcategory_update.title
        subcategory.category_id = subcategory_update.category_id
        await self.session.flush()
        await self.session.refresh(subcategory)
        return subcategory

    async def delete_subcategory(self, subcategory: Subcategory) -> None:
        await self.session.delete(subcategory)
