from typing import Protocol
from uuid import UUID

from pydantic import UUID4
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import DocumentHistory


class HistoryRepository(Protocol):
    async def create_document_history(
        self, document_id: UUID, action: str, description: str, created_by: UUID
    ) -> DocumentHistory: ...

    async def get_document_histories_paginated(
        self,
        skip: int,
        limit: int,
        search: str | None = None,
        user_id: UUID4 | None = None,
    ) -> list[DocumentHistory]: ...

    async def count_document_histories(
        self, search: str | None = None, user_id: UUID4 | None = None
    ) -> int: ...


class HistoryRepositoryImpl:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_document_history(
        self, document_id: UUID, action: str, description: str, created_by: UUID
    ) -> DocumentHistory:
        document_history = DocumentHistory(
            document_id=document_id,
            action=action,
            description=description,
            created_by=created_by,
        )
        self.session.add(document_history)
        await self.session.flush()
        await self.session.refresh(document_history)
        return document_history

    async def get_document_histories_paginated(
        self,
        skip: int,
        limit: int,
        search: str | None = None,
        user_id: UUID4 | None = None,
    ) -> list[DocumentHistory]:
        query = select(DocumentHistory)

        if user_id:
            query = query.where(DocumentHistory.created_by == user_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (DocumentHistory.action.ilike(search_pattern))
                | (DocumentHistory.description.ilike(search_pattern))
            )

        query = query.options(
            selectinload(DocumentHistory.document),
            selectinload(DocumentHistory.creator),
        )

        query = query.order_by(DocumentHistory.created_at.desc())

        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_document_histories(
        self, search: str | None = None, user_id: UUID4 | None = None
    ) -> int:
        query = select(func.count(DocumentHistory.id))

        if user_id:
            query = query.where(DocumentHistory.created_by == user_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (DocumentHistory.action.ilike(search_pattern))
                | (DocumentHistory.description.ilike(search_pattern))
            )

        result = await self.session.execute(query)
        return result.scalar() or 0
