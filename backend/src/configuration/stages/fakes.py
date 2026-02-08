from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import UUID4
from starlette import status

from configuration.models import Stage
from configuration.stages.repository import StageRepository
from configuration.stages.schemas import (
    PaginatedStageResponse,
    StageCreate,
    StageResponse,
    StageUpdate,
)
from configuration.stages.service import StageService
from schemas import Error, Message


class FakeStageRepository(StageRepository):
    def __init__(self, session: Any = None):
        self.session = session
        self.stages: dict[UUID, Stage] = {}

    async def get_all_stages_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
    ) -> list[Stage]:
        all_stages = list(self.stages.values())

        if search:
            search_lower = search.lower()
            all_stages = [s for s in all_stages if search_lower in s.title.lower()]

        return sorted(all_stages, key=lambda x: x.title)[skip : skip + limit]

    async def count_stages(
        self,
        search: str | None = None,
    ) -> int:
        all_stages = list(self.stages.values())

        if search:
            search_lower = search.lower()
            all_stages = [s for s in all_stages if search_lower in s.title.lower()]

        return len(all_stages)

    async def check_title_exists(self, title: str) -> bool:
        return any(s.title.lower() == title.lower() for s in self.stages.values())

    async def check_title_exists_excluding_id(
        self, title: str, stage_id: UUID4
    ) -> bool:
        return any(
            s.title.lower() == title.lower() and s.id != stage_id
            for s in self.stages.values()
        )

    async def get_stage_by_id(self, stage_id: UUID4) -> Stage | None:
        return self.stages.get(stage_id)

    async def create_stage(self, stage_create: StageCreate) -> Stage:
        stage = Stage(
            id=uuid4(),
            title=stage_create.title,
            color=stage_create.color,
            created_at=datetime.now(UTC),
        )
        self.stages[stage.id] = stage
        return stage

    async def update_stage(self, stage: Stage, stage_update: StageUpdate) -> Stage:
        stage.title = stage_update.title
        stage.color = stage_update.color
        stage.updated_at = datetime.now(UTC)
        return stage

    async def delete_stage(self, stage: Stage) -> None:
        if stage.id in self.stages:
            del self.stages[stage.id]


class FakeStageService(StageService):
    def __init__(self) -> None:
        self.stages: dict[UUID, Stage] = {}

    async def get_all_stages_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> PaginatedStageResponse | Error:
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

        skip = (page - 1) * page_size

        all_stages = list(self.stages.values())

        if search:
            search_lower = search.lower()
            all_stages = [s for s in all_stages if search_lower in s.title.lower()]

        sorted_stages = sorted(all_stages, key=lambda x: x.title)
        paginated_stages = sorted_stages[skip : skip + page_size]

        total_rows = len(all_stages)
        total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 0

        return PaginatedStageResponse(
            data=[StageResponse.model_validate(stage) for stage in paginated_stages],
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    async def create_stage(self, stage_create: StageCreate) -> Stage | Error:
        title_exists = any(
            s.title.lower() == stage_create.title.lower() for s in self.stages.values()
        )
        if title_exists:
            return Error(
                detail="Stage title already exists", code=status.HTTP_400_BAD_REQUEST
            )

        stage = Stage(
            id=uuid4(),
            title=stage_create.title,
            color=stage_create.color,
            created_at=datetime.now(UTC),
        )
        self.stages[stage.id] = stage
        return stage

    async def update_stage(
        self, stage_id: UUID4, stage_update: StageUpdate
    ) -> Stage | Error:
        stage = self.stages.get(stage_id)
        if not stage:
            return Error(detail="Stage not found", code=status.HTTP_404_NOT_FOUND)

        if stage.title != stage_update.title:
            title_exists = any(
                s.title.lower() == stage_update.title.lower() and s.id != stage_id
                for s in self.stages.values()
            )
            if title_exists:
                return Error(
                    detail="Stage title already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

        stage.title = stage_update.title
        stage.color = stage_update.color
        stage.updated_at = datetime.now(UTC)
        return stage

    async def get_stage_by_id(self, stage_id: UUID4) -> Stage | Error:
        stage = self.stages.get(stage_id)
        if not stage:
            return Error(detail="Stage not found", code=status.HTTP_404_NOT_FOUND)
        return stage

    async def delete_stage(self, stage_id: UUID4) -> Message | Error:
        stage = self.stages.get(stage_id)
        if not stage:
            return Error(detail="Stage not found", code=status.HTTP_404_NOT_FOUND)
        del self.stages[stage_id]
        return Message(detail="Stage deleted successfully")
