import logging
from datetime import datetime
from typing import Protocol

from dependency_injector.wiring import Provide, inject
from pydantic import UUID4

from auth.logged_histories.schemas import (
    LoggedHistoryResponse,
    PaginatedLoggedHistoryResponse,
)
from auth.models import LoggedHistoryType
from schemas import Error
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
