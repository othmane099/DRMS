from datetime import datetime
from typing import Protocol

from pydantic import UUID4
from sqlalchemy import cast, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.types import String

from auth.logged_histories.schemas import LoggedHistoryCreate
from auth.models import LoggedHistory, LoggedHistoryType


class LoggedHistoryRepository(Protocol):
    async def get_all_logged_histories_paginated(
        self,
        skip: int,
        limit: int,
        user_id: UUID4 | None = None,
        type_filter: LoggedHistoryType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> list[LoggedHistory]: ...

    async def count_logged_histories(
        self,
        user_id: UUID4 | None = None,
        type_filter: LoggedHistoryType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> int: ...

    async def create_logged_history(
        self, logged_history_create: LoggedHistoryCreate
    ) -> LoggedHistory | None: ...


def _build_filter_query(
    query,
    user_id: UUID4 | None = None,
    type_filter: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
):
    query = query.where(LoggedHistory.deleted_at.is_(None))

    if user_id:
        query = query.where(LoggedHistory.user_id == user_id)
    if type_filter:
        query = query.where(LoggedHistory.type == type_filter)
    if date_from:
        query = query.where(LoggedHistory.date >= date_from)
    if date_to:
        query = query.where(LoggedHistory.date <= date_to)
    if search:
        query = query.where(cast(LoggedHistory.details, String).ilike(f"%{search}%"))

    return query


class LoggedHistoryRepositoryImpl(LoggedHistoryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

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
        query = select(LoggedHistory).options(selectinload(LoggedHistory.user))
        query = _build_filter_query(
            query, user_id, type_filter, date_from, date_to, search
        )
        query = query.order_by(LoggedHistory.date.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def count_logged_histories(
        self,
        user_id: UUID4 | None = None,
        type_filter: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> int:
        query = select(func.count(LoggedHistory.id))
        query = _build_filter_query(
            query, user_id, type_filter, date_from, date_to, search
        )

        result = await self.session.execute(query)
        return result.scalar_one()

    async def create_logged_history(
        self, logged_history_create: LoggedHistoryCreate
    ) -> LoggedHistory | None:
        stmt = (
            insert(LoggedHistory)
            .values(**logged_history_create.model_dump())
            .returning(LoggedHistory)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
