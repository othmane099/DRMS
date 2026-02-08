import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import UUID4
from starlette import status

from auth.logged_histories.repository import LoggedHistoryRepository
from auth.logged_histories.schemas import (
    LoggedHistoryCreate,
    LoggedHistoryResponse,
    PaginatedLoggedHistoryResponse,
)
from auth.logged_histories.service import LoggedHistoryService
from auth.models import LoggedHistory
from schemas import Error, Message


class FakeLoggedHistoryRepository(LoggedHistoryRepository):
    def __init__(self, session: Any = None):
        self.session = session
        self.logged_histories: dict[UUID, LoggedHistory] = {}

    def _apply_filters(
        self,
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
        filtered = self._apply_filters(
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
        filtered = self._apply_filters(
            list(self.logged_histories.values()),
            user_id,
            type_filter,
            date_from,
            date_to,
            search,
        )
        return len(filtered)

    async def get_logged_history_by_id(
        self, logged_history_id: UUID4
    ) -> LoggedHistory | None:
        lh = self.logged_histories.get(logged_history_id)
        if lh and lh.deleted_at is None:
            return lh
        return None

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

    async def delete_logged_history(self, logged_history: LoggedHistory) -> None:
        logged_history.deleted_at = datetime.now()


class FakeLoggedHistoryService(LoggedHistoryService):
    def __init__(self) -> None:
        self.logged_histories: dict[UUID, LoggedHistory] = {}

    def _apply_filters(
        self,
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

        filtered = self._apply_filters(
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

    async def get_logged_history_by_id(
        self, logged_history_id: UUID
    ) -> LoggedHistory | Error:
        lh = self.logged_histories.get(logged_history_id)
        if lh and lh.deleted_at is None:
            return lh
        return Error(detail="Logged history not found", code=status.HTTP_404_NOT_FOUND)

    async def create_logged_history(
        self, logged_history_create: LoggedHistoryCreate, uow=None
    ) -> LoggedHistory | Error:
        logged_history = LoggedHistory(
            id=uuid4(),
            user_id=logged_history_create.user_id,
            ip=logged_history_create.ip,
            date=logged_history_create.date,
            details=logged_history_create.details,
            type=logged_history_create.type,
            created_at=datetime.now(),
        )
        self.logged_histories[logged_history.id] = logged_history
        return logged_history

    async def delete_logged_history(self, logged_history_id: UUID4) -> Message | Error:
        lh = self.logged_histories.get(logged_history_id)
        if not lh or lh.deleted_at is not None:
            return Error(
                detail="Logged history not found", code=status.HTTP_404_NOT_FOUND
            )

        lh.deleted_at = datetime.now()
        return Message(detail="Logged history deleted successfully")

    async def delete_all_logged_histories(self) -> Message | Error:
        for lh in self.logged_histories.values():
            if lh.deleted_at is None:
                lh.deleted_at = datetime.now()
        return Message(detail="All logged histories deleted successfully")
