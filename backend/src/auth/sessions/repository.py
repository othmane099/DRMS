from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from auth.models import Session, User


class SessionRepository(Protocol):
    async def get_active_session(
        self, session_token: str, will_expire_at: datetime
    ) -> Session | None: ...

    async def create_session(
        self,
        user_id: UUID,
        session_token: str,
        expired_at: datetime,
    ) -> Session: ...


class SessionRepositoryImpl(SessionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_session(
        self, session_token: str, will_expire_at: datetime
    ) -> Session | None:
        result = await self.session.execute(
            select(Session)
            .options(
                selectinload(Session.user).selectinload(User.role),
                selectinload(Session.user).selectinload(User.custom_permissions),
            )
            .where(
                Session.token == session_token,
                Session.is_active.is_(True),
                Session.expired_at > will_expire_at,
                Session.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_session(
        self,
        user_id: UUID,
        session_token: str,
        expired_at: datetime,
    ) -> Session:
        session = Session(
            token=session_token,
            user_id=user_id,
            expired_at=expired_at,
        )
        self.session.add(session)
        return session
