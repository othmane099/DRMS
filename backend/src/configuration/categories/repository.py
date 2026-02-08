from typing import Protocol

from pydantic import UUID4
from sqlalchemy import Row, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from configuration.categories.schemas import CategoryCreate, CategoryUpdate
from configuration.models import Category, Subcategory


class CategoryRepository(Protocol):
    async def get_all_categories_paginated(
        self,
        skip: int,
        limit: int,
        search: str | None = None,
    ) -> list[Row[tuple[Category, int]]]: ...

    async def count_categories(self, search: str | None = None) -> int: ...

    async def check_title_exists(self, title: str) -> bool: ...

    async def get_category_by_id(self, category_id: UUID4) -> Category | None: ...

    async def create_category(self, category_create: CategoryCreate) -> Category: ...

    async def update_category(
        self, category: Category, category_update: CategoryUpdate
    ) -> Category: ...

    async def delete_category(self, category: Category) -> None: ...


class CategoryRepositoryImpl(CategoryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_categories_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
    ) -> list[Row[tuple[Category, int]]]:
        subcategory_count = (
            select(func.count(Subcategory.id))
            .where(Subcategory.category_id == Category.id)
            .correlate(Category)
            .scalar_subquery()
            .label("subcategory_count")
        )

        query = select(Category, subcategory_count)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(Category.title.ilike(search_pattern))

        query = query.order_by(Category.created_at).offset(skip).limit(limit)
        result = await self.session.execute(query)

        return list(result.all())

    async def count_categories(self, search: str | None = None) -> int:
        query = select(func.count(Category.id))

        if search:
            search_pattern = f"%{search}%"
            query = query.where(Category.title.ilike(search_pattern))

        result = await self.session.execute(query)
        return result.scalar_one()

    async def check_title_exists(self, title: str) -> bool:
        query = select(func.count(Category.id)).where(
            func.lower(Category.title) == title.lower()
        )
        result = await self.session.execute(query)
        return result.scalar_one() > 0

    async def get_category_by_id(self, category_id: UUID4) -> Category | None:
        query = (
            select(Category)
            .where(Category.id == category_id)
            .options(selectinload(Category.subcategories))
        )
        result = await self.session.execute(query)
        category = result.scalar_one_or_none()
        return category

    async def create_category(self, category_create: CategoryCreate) -> Category:
        stmt = (
            insert(Category).values(**category_create.model_dump()).returning(Category)
        )
        result = await self.session.execute(stmt)
        category = result.scalar_one()
        await self.session.refresh(category, attribute_names=["subcategories"])
        return category

    async def update_category(
        self, category: Category, category_update: CategoryUpdate
    ) -> Category:
        category.title = category_update.title
        await self.session.flush()
        await self.session.refresh(category, attribute_names=["subcategories"])
        return category

    async def delete_category(self, category: Category) -> None:
        await self.session.delete(category)
