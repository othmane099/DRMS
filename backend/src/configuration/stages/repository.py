from typing import Protocol

from pydantic import UUID4
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from configuration.models import Stage
from configuration.stages.schemas import StageCreate, StageUpdate


class StageRepository(Protocol):
    async def get_all_stages_paginated(
        self,
        skip: int,
        limit: int,
        search: str | None = None,
    ) -> list[Stage]: ...

    async def count_stages(self, search: str | None = None) -> int: ...

    async def check_title_exists(self, title: str) -> bool: ...

    async def get_stage_by_id(self, stage_id: UUID4) -> Stage | None: ...

    async def create_stage(self, stage_create: StageCreate) -> Stage: ...

    async def update_stage(self, stage: Stage, stage_update: StageUpdate) -> Stage: ...

    async def delete_stage(self, stage: Stage) -> None: ...


class StageRepositoryImpl(StageRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_stages_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
    ) -> list[Stage]:
        query = select(Stage)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(Stage.title.ilike(search_pattern))

        query = query.order_by(Stage.created_at).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_stages(self, search: str | None = None) -> int:
        query = select(func.count(Stage.id))

        if search:
            search_pattern = f"%{search}%"
            query = query.where(Stage.title.ilike(search_pattern))

        result = await self.session.execute(query)
        return result.scalar_one()

    async def check_title_exists(self, title: str) -> bool:
        query = select(func.count(Stage.id)).where(
            func.lower(Stage.title) == title.lower()
        )
        result = await self.session.execute(query)
        return result.scalar_one() > 0

    async def get_stage_by_id(self, stage_id: UUID4) -> Stage | None:
        query = select(Stage).where(Stage.id == stage_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_stage(self, stage_create: StageCreate) -> Stage:
        stmt = insert(Stage).values(**stage_create.model_dump()).returning(Stage)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_stage(self, stage: Stage, stage_update: StageUpdate) -> Stage:
        stage.title = stage_update.title
        stage.color = stage_update.color
        await self.session.flush()
        await self.session.refresh(stage)
        return stage

    async def delete_stage(self, stage: Stage) -> None:
        await self.session.delete(stage)
