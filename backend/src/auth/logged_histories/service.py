import logging
from datetime import datetime
from typing import Protocol
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from pydantic import UUID4
from starlette import status

from auth.logged_histories.schemas import (
    LoggedHistoryCreate,
    LoggedHistoryResponse,
    PaginatedLoggedHistoryResponse,
)
from auth.models import LoggedHistory, LoggedHistoryType
from schemas import Error, Message
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)


class LoggedHistoryService(Protocol):
    async def get_all_logged_histories_paginated(
        self,
        page: int,
        page_size: int,
        user_id: UUID4 | None = None,
        type_filter: LoggedHistoryType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> PaginatedLoggedHistoryResponse | Error: ...

    async def get_logged_history_by_id(
        self, logged_history_id: UUID
    ) -> LoggedHistory | Error: ...

    async def create_logged_history(
        self, logged_history_create: LoggedHistoryCreate, uow: UnitOfWork
    ) -> LoggedHistory | Error: ...

    async def delete_logged_history(
        self, logged_history_id: UUID4
    ) -> Message | Error: ...

    async def delete_all_logged_histories(self) -> Message | Error: ...


class LoggedHistoryServiceImpl(LoggedHistoryService):
    @inject
    def __init__(self, unit_of_work: UnitOfWork = Provide["unit_of_work"]):
        self._unit_of_work = unit_of_work

    async def get_all_logged_histories_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        user_id: UUID4 | None = None,
        type_filter: LoggedHistoryType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> PaginatedLoggedHistoryResponse | Error:
        logger.debug(
            "Fetching logged histories (page=%s, page_size=%s, user_id=%s, type=%s)",
            page,
            page_size,
            user_id,
            type_filter,
        )

        skip = (page - 1) * page_size
        limit = page_size

        async with self._unit_of_work as uow:
            logged_histories = (
                await uow.logged_history_repository.get_all_logged_histories_paginated(
                    skip=skip,
                    limit=limit,
                    user_id=user_id,
                    type_filter=type_filter,
                    date_from=date_from,
                    date_to=date_to,
                    search=search,
                )
            )
            total_rows = await uow.logged_history_repository.count_logged_histories(
                user_id=user_id,
                type_filter=type_filter,
                date_from=date_from,
                date_to=date_to,
                search=search,
            )

        total_pages = (total_rows + page_size - 1) // page_size

        response_data = []
        for lh in logged_histories:
            user_name = None
            if lh.user:
                user_name = f"{lh.user.first_name} {lh.user.last_name}"
            response_data.append(
                LoggedHistoryResponse(
                    id=lh.id,
                    user_id=lh.user_id,
                    user_name=user_name,
                    ip=lh.ip,
                    date=lh.date,
                    details=lh.details,
                    type=lh.type,
                )
            )

        logger.info(
            "Logged histories fetched (page=%s, page_size=%s, total_rows=%s)",
            page,
            page_size,
            total_rows,
        )
        return PaginatedLoggedHistoryResponse(
            data=response_data,
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    async def get_logged_history_by_id(
        self, logged_history_id: UUID
    ) -> LoggedHistory | Error:
        logger.debug("Fetching logged history by id=%s", logged_history_id)

        async with self._unit_of_work as uow:
            logged_history = (
                await uow.logged_history_repository.get_logged_history_by_id(
                    logged_history_id
                )
            )
            if not logged_history:
                logger.warning("Logged history not found (id=%s)", logged_history_id)
                return Error(
                    detail="Logged history not found", code=status.HTTP_404_NOT_FOUND
                )

            logger.debug("Logged history found (id=%s)", logged_history_id)
            return logged_history

    async def create_logged_history(
        self, logged_history_create: LoggedHistoryCreate, uow: UnitOfWork
    ) -> LoggedHistory | Error:
        logger.info(
            "Creating logged history (type=%s, user_id=%s)",
            logged_history_create.type,
            logged_history_create.user_id,
        )

        instance = await uow.logged_history_repository.create_logged_history(
            logged_history_create
        )
        await uow.commit()
        created_logged_history = (
            await uow.logged_history_repository.get_logged_history_by_id(instance.id)
        )

        logger.info(
            "Logged history created successfully (id=%s)", created_logged_history.id
        )
        return created_logged_history

    async def delete_logged_history(self, logged_history_id: UUID4) -> Message | Error:
        logger.info("Deleting logged history (id=%s)", logged_history_id)

        async with self._unit_of_work as uow:
            logged_history = (
                await uow.logged_history_repository.get_logged_history_by_id(
                    logged_history_id
                )
            )
            if not logged_history:
                logger.warning(
                    "Logged history deletion failed: not found (id=%s)",
                    logged_history_id,
                )
                return Error(
                    detail="Logged history not found", code=status.HTTP_404_NOT_FOUND
                )
            await uow.logged_history_repository.delete_logged_history(logged_history)
            await uow.commit()

        logger.info("Logged history deleted successfully (id=%s)", logged_history_id)
        return Message(detail="Logged history deleted successfully")

    async def delete_all_logged_histories(self) -> Message | Error:
        logger.info("Deleting all logged histories")

        async with self._unit_of_work as uow:
            logged_histories = (
                await uow.logged_history_repository.get_all_logged_histories_paginated(
                    skip=0, limit=10000
                )
            )
            for lh in logged_histories:
                await uow.logged_history_repository.delete_logged_history(lh)
            await uow.commit()

        logger.info("All logged histories deleted successfully")
        return Message(detail="All logged histories deleted successfully")
