import logging
from typing import Protocol

from dependency_injector.wiring import Provide, inject
from pydantic import UUID4
from starlette import status

from configuration.models import Stage
from configuration.stages.schemas import (
    PaginatedStageResponse,
    StageCreate,
    StageResponse,
    StageUpdate,
)
from schemas import Error, Message
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)


class StageService(Protocol):
    async def get_all_stages_paginated(
        self,
        page: int,
        page_size: int,
        search: str | None = None,
    ) -> PaginatedStageResponse | Error: ...

    async def create_stage(self, stage_create: StageCreate) -> Stage | Error: ...

    async def update_stage(
        self, stage_id: UUID4, stage_update: StageUpdate
    ) -> Stage | Error: ...

    async def get_stage_by_id(self, stage_id: UUID4) -> Stage | Error: ...

    async def delete_stage(self, stage_id: UUID4) -> Message | Error: ...


class StageServiceImpl(StageService):
    @inject
    def __init__(self, unit_of_work: UnitOfWork = Provide["unit_of_work"]):
        self._unit_of_work = unit_of_work

    async def get_all_stages_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> PaginatedStageResponse | Error:
        logger.debug(
            "Fetching stages (page=%s, page_size=%s, search=%s)",
            page,
            page_size,
            search,
        )

        skip = (page - 1) * page_size
        limit = page_size

        async with self._unit_of_work as uow:
            stages = await uow.stage_repository.get_all_stages_paginated(
                skip=skip,
                limit=limit,
                search=search,
            )
            total_rows = await uow.stage_repository.count_stages(
                search=search,
            )

        total_pages = (total_rows + page_size - 1) // page_size

        logger.info(
            "Stages fetched (page=%s, page_size=%s, total_rows=%s, total_pages=%s)",
            page,
            page_size,
            total_rows,
            total_pages,
        )
        return PaginatedStageResponse(
            data=[StageResponse.model_validate(stage) for stage in stages],
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    async def create_stage(self, stage_create: StageCreate) -> Stage | Error:
        logger.info("Creating stage (title=%s)", stage_create.title)
        async with self._unit_of_work as uow:
            title_exists = await uow.stage_repository.check_title_exists(
                stage_create.title
            )
            if title_exists:
                logger.warning(
                    "Stage creation rejected: title already exists (title=%s)",
                    stage_create.title,
                )
                return Error(
                    detail="Stage title already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

            stage = await uow.stage_repository.create_stage(stage_create)
            await uow.commit()

        logger.info(
            "Stage created successfully (id=%s, title=%s)",
            stage.id,
            stage.title,
        )
        return stage

    async def update_stage(
        self, stage_id: UUID4, stage_update: StageUpdate
    ) -> Stage | Error:
        logger.info("Updating stage (id=%s)", stage_id)

        async with self._unit_of_work as uow:
            existing_stage = await uow.stage_repository.get_stage_by_id(stage_id)
            if not existing_stage:
                logger.warning("Stage update failed: not found (id=%s)", stage_id)
                return Error(detail="Stage not found", code=status.HTTP_404_NOT_FOUND)

            if existing_stage.title != stage_update.title:
                title_exists = await uow.stage_repository.check_title_exists(
                    stage_update.title
                )
                if title_exists:
                    logger.warning(
                        "Stage update rejected: title conflict (id=%s, title=%s)",
                        stage_id,
                        stage_update.title,
                    )
                    return Error(
                        detail="Stage title already exists",
                        code=status.HTTP_400_BAD_REQUEST,
                    )

            updated_stage = await uow.stage_repository.update_stage(
                existing_stage, stage_update
            )
            await uow.commit()

        logger.info("Stage updated successfully (id=%s)", stage_id)
        return updated_stage

    async def get_stage_by_id(self, stage_id: UUID4) -> Stage | Error:
        logger.debug("Fetching stage by id=%s", stage_id)

        async with self._unit_of_work as uow:
            stage = await uow.stage_repository.get_stage_by_id(stage_id)
            if not stage:
                logger.warning("Stage not found (id=%s)", stage_id)
                return Error(detail="Stage not found", code=status.HTTP_404_NOT_FOUND)

            logger.debug("Stage found (id=%s)", stage_id)
            return stage

    async def delete_stage(self, stage_id: UUID4) -> Message | Error:
        logger.info("Deleting stage (id=%s)", stage_id)

        async with self._unit_of_work as uow:
            stage_to_delete = await uow.stage_repository.get_stage_by_id(stage_id)
            if not stage_to_delete:
                logger.warning("Stage deletion failed: not found (id=%s)", stage_id)
                return Error(detail="Stage not found", code=status.HTTP_404_NOT_FOUND)

            await uow.stage_repository.delete_stage(stage_to_delete)
            await uow.commit()

        logger.info("Stage deleted successfully (id=%s)", stage_id)
        return Message(detail="Stage deleted successfully")
