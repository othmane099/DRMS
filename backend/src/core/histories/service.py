import logging
from typing import Protocol

from pydantic import UUID4

from auth.models import User
from core.documents.service import _permission_checker
from core.histories.schemas import (
    DocumentHistoryResponse,
    PaginatedDocumentHistoryResponse,
)
from schemas import Error
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)


class HistoryService(Protocol):
    async def get_document_histories_paginated(
        self,
        page: int,
        page_size: int,
        search: str | None = None,
        current_user: User | None = None,
    ) -> PaginatedDocumentHistoryResponse | Error: ...


class HistoryServiceImpl:
    def __init__(self, unit_of_work: UnitOfWork):
        self._unit_of_work = unit_of_work

    async def get_document_histories_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        current_user: User | None = None,
    ) -> PaginatedDocumentHistoryResponse | Error:
        logger.debug(
            "Fetching document histories (page=%s, page_size=%s, search=%s)",
            page,
            page_size,
            search,
        )

        user_id: UUID4 | None = None
        if current_user is not None:
            result = await _permission_checker(
                current_user, "documents.history", "documents.history_my"
            )
            if isinstance(result, Error):
                return result
            can_view_all = result is None or "documents.history" in result
            user_id = None if can_view_all else current_user.id

        skip = (page - 1) * page_size
        limit = page_size

        async with self._unit_of_work as uow:
            histories = await uow.history_repository.get_document_histories_paginated(
                skip=skip, limit=limit, search=search, user_id=user_id
            )
            total_rows = await uow.history_repository.count_document_histories(
                search=search, user_id=user_id
            )

        total_pages = (total_rows + page_size - 1) // page_size

        logger.info(
            "Document histories fetched (page=%s, page_size=%s, total_rows=%s, total_pages=%s)",
            page,
            page_size,
            total_rows,
            total_pages,
        )
        return PaginatedDocumentHistoryResponse(
            data=[DocumentHistoryResponse.model_validate(h) for h in histories],
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )
