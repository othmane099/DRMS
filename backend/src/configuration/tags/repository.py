from typing import Protocol

from pydantic import UUID4
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from configuration.models import Tag
from configuration.tags.schemas import TagCreate, TagUpdate


class TagRepository(Protocol):
    async def get_all_tags_paginated(
        self,
        skip: int,
        limit: int,
        search: str | None = None,
    ) -> list[Tag]: ...

    async def count_tags(self, search: str | None = None) -> int: ...

    async def check_title_exists(self, title: str) -> bool: ...

    async def get_tag_by_id(self, tag_id: UUID4) -> Tag | None: ...

    async def create_tag(self, tag_create: TagCreate) -> Tag: ...

    async def update_tag(self, tag: Tag, tag_update: TagUpdate) -> Tag: ...

    async def delete_tag(self, tag: Tag) -> None: ...


class TagRepositoryImpl(TagRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_tags_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
    ) -> list[Tag]:
        query = select(Tag)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(Tag.title.ilike(search_pattern))

        query = query.order_by(Tag.title).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_tags(self, search: str | None = None) -> int:
        query = select(func.count(Tag.id))

        if search:
            search_pattern = f"%{search}%"
            query = query.where(Tag.title.ilike(search_pattern))

        result = await self.session.execute(query)
        return result.scalar_one()

    async def check_title_exists(self, title: str) -> bool:
        query = select(func.count(Tag.id)).where(func.lower(Tag.title) == title.lower())
        result = await self.session.execute(query)
        return result.scalar_one() > 0

    async def get_tag_by_id(self, tag_id: UUID4) -> Tag | None:
        query = select(Tag).where(Tag.id == tag_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_tag(self, tag_create: TagCreate) -> Tag:
        stmt = insert(Tag).values(**tag_create.model_dump()).returning(Tag)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_tag(self, tag: Tag, tag_update: TagUpdate) -> Tag:
        tag.title = tag_update.title
        await self.session.flush()
        await self.session.refresh(tag)
        return tag

    async def delete_tag(self, tag: Tag) -> None:
        await self.session.delete(tag)
