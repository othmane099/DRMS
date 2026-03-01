from datetime import datetime
from uuid import UUID, uuid4

from pydantic import UUID4

from core.histories.schemas import (
    DocumentHistoryResponse,
    PaginatedDocumentHistoryResponse,
)
from core.models import DocumentHistory
from schemas import Error


class FakeHistoryRepository:
    def __init__(self):
        self.document_histories: dict[UUID, DocumentHistory] = {}

    async def create_document_history(
        self, document_id: UUID, action: str, description: str, created_by: UUID
    ) -> DocumentHistory:
        document_history = DocumentHistory(
            id=uuid4(),
            document_id=document_id,
            action=action,
            description=description,
            created_by=created_by,
            created_at=datetime.now(),
        )
        self.document_histories[document_history.id] = document_history
        return document_history

    async def get_document_histories_paginated(
        self,
        skip: int,
        limit: int,
        search: str | None = None,
        user_id: UUID4 | None = None,
    ) -> list[DocumentHistory]:
        histories = list(self.document_histories.values())

        if user_id:
            histories = [h for h in histories if h.created_by == user_id]

        if search:
            search_lower = search.lower()
            histories = [
                h
                for h in histories
                if search_lower in h.action.lower()
                or search_lower in h.description.lower()
            ]

        histories.sort(key=lambda x: x.created_at, reverse=True)

        return histories[skip : skip + limit]

    async def count_document_histories(
        self, search: str | None = None, user_id: UUID4 | None = None
    ) -> int:
        histories = list(self.document_histories.values())

        if user_id:
            histories = [h for h in histories if h.created_by == user_id]

        if search:
            search_lower = search.lower()
            histories = [
                h
                for h in histories
                if search_lower in h.action.lower()
                or search_lower in h.description.lower()
            ]

        return len(histories)


class FakeHistoryService:
    def __init__(self):
        self.document_histories: dict[UUID, DocumentHistory] = {}

    async def get_document_histories_paginated(
        self,
        page: int,
        page_size: int,
        search: str | None = None,
        current_user=None,
    ) -> PaginatedDocumentHistoryResponse | Error:
        histories = list(self.document_histories.values())

        user_id = current_user.id if current_user else None
        if user_id:
            histories = [h for h in histories if h.created_by == user_id]

        if search:
            search_lower = search.lower()
            histories = [
                h
                for h in histories
                if search_lower in h.action.lower()
                or search_lower in h.description.lower()
            ]

        histories.sort(key=lambda x: x.created_at, reverse=True)

        total_rows = len(histories)
        total_pages = (total_rows + page_size - 1) // page_size
        skip = (page - 1) * page_size

        paginated_histories = histories[skip : skip + page_size]

        return PaginatedDocumentHistoryResponse(
            data=[
                DocumentHistoryResponse.model_validate(h) for h in paginated_histories
            ],
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )
