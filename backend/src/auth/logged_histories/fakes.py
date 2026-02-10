import json
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import UUID4

from auth.logged_histories.repository import LoggedHistoryRepository
from auth.logged_histories.schemas import (
    LoggedHistoryCreate,
    LoggedHistoryResponse,
    PaginatedLoggedHistoryResponse,
)
from auth.logged_histories.service import LoggedHistoryService
from auth.models import LoggedHistory
from schemas import Error


def _apply_filters(
    logged_histories: list[LoggedHistory],
    user_id: UUID4 | None = None,
    type_filter: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
) -> list[LoggedHistory]:
    result = [lh for lh in logged_histories if lh.deleted_at is None]

    if user_id:
        result = [lh for lh in result if lh.user_id == user_id]
    if type_filter:
        result = [lh for lh in result if lh.type == type_filter]
    if date_from:
        result = [lh for lh in result if lh.date and lh.date >= date_from]
    if date_to:
        result = [lh for lh in result if lh.date and lh.date <= date_to]
    if search:
        result = [
            lh
            for lh in result
            if lh.details and search.lower() in json.dumps(lh.details).lower()
        ]

    return result


class FakeLoggedHistoryRepository(LoggedHistoryRepository):
    def __init__(self):
        self.logged_histories: dict[UUID, LoggedHistory] = {}

    async def get_all_logged_histories_paginated(
        self,
        skip: int = 0,
        limit: int = 10,
        user_id: UUID4 | None = None,
        type_filter: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> list[LoggedHistory]:
        filtered = _apply_filters(
            list(self.logged_histories.values()),
            user_id,
            type_filter,
            date_from,
            date_to,
            search,
        )
        sorted_histories = sorted(
            filtered, key=lambda x: x.date or datetime.min, reverse=True
        )
        return sorted_histories[skip : skip + limit]

    async def count_logged_histories(
        self,
        user_id: UUID4 | None = None,
        type_filter: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> int:
        filtered = _apply_filters(
            list(self.logged_histories.values()),
            user_id,
            type_filter,
            date_from,
            date_to,
            search,
        )
        return len(filtered)

    async def create_logged_history(
        self, logged_history_create: LoggedHistoryCreate
    ) -> LoggedHistory | None:
        logged_history = LoggedHistory(
            id=uuid4(),
            user_id=logged_history_create.user_id,
            ip=logged_history_create.ip,
            date=logged_history_create.date,
            details=logged_history_create.details,
            type=logged_history_create.type,
            created_at=datetime.now(),
        )
        self.logged_histories[UUID(str(logged_history.id))] = logged_history
        return logged_history


class FakeLoggedHistoryService(LoggedHistoryService):
    def __init__(self) -> None:
        self.logged_histories: dict[UUID, LoggedHistory] = {}

    async def get_all_logged_histories_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        user_id: UUID4 | None = None,
        type_filter: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> PaginatedLoggedHistoryResponse | Error:
        skip = (page - 1) * page_size

        filtered = _apply_filters(
            list(self.logged_histories.values()),
            user_id,
            type_filter,
            date_from,
            date_to,
            search,
        )
        sorted_histories = sorted(
            filtered, key=lambda x: x.date or datetime.min, reverse=True
        )
        paginated = sorted_histories[skip : skip + page_size]

        total_rows = len(filtered)
        total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 0

        response_data = []
        for lh in paginated:
            response_data.append(
                LoggedHistoryResponse(
                    id=lh.id,
                    user_id=lh.user_id,
                    user_name=None,
                    ip=lh.ip,
                    date=lh.date,
                    details=lh.details,
                    type=lh.type,
                )
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
