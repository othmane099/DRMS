import secrets
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytz
from starlette import status

from auth.models import Session
from auth.sessions.repository import SessionRepository
from auth.sessions.service import SessionService
from schemas import Error, Message
from unit_of_work.uow import UnitOfWork


class FakeSessionRepository(SessionRepository):
    def __init__(self, session: Any = None):
        self.session = session
        self.sessions: dict[UUID, Session] = {}

    async def get_active_session(
        self, session_token: str, will_expire_at: datetime
    ) -> Session | None:
        for sess in self.sessions.values():
            if (
                sess.token == session_token
                and sess.is_active
                and sess.expired_at > will_expire_at
                and sess.deleted_at is None
            ):
                return sess
        return None

    async def create_session(
        self,
        user_id: UUID,
        session_token: str,
        expired_at: datetime,
    ) -> Session:
        session = Session(
            id=uuid4(),
            token=session_token,
            user_id=user_id,
            expired_at=expired_at,
            is_active=True,
            created_at=datetime.now(pytz.utc),
        )
        self.sessions[session.id] = session
        return session


class FakeSessionService(SessionService):
    def __init__(self):
        self.sessions: dict[str, Session] = {}

    async def generate_session_token(self) -> str:
        return secrets.token_urlsafe(32)

    async def create_session(
        self,
        user_id: UUID,
        uow: UnitOfWork,
        hours_valid: int = 24,
    ) -> Session:
        session_token = await self.generate_session_token()
        expired_at = datetime.now(pytz.utc) + timedelta(hours=hours_valid)

        session = Session(
            id=uuid4(),
            token=session_token,
            user_id=user_id,
            expired_at=expired_at,
            is_active=True,
            created_at=datetime.now(pytz.utc),
        )
        self.sessions[session_token] = session
        return session

    async def get_active_session(self, session_token: str) -> Session | Error:
        will_expire_at = datetime.now(pytz.utc)
        session = self.sessions.get(session_token)

        if (
            session
            and session.is_active
            and session.expired_at > will_expire_at
            and session.deleted_at is None
        ):
            return session

        return Error(
            detail="Session not found or expired",
            code=status.HTTP_401_UNAUTHORIZED,
        )

    async def invalidate_session(self, session_token: str) -> Message | Error:
        will_expire_at = datetime.now(pytz.utc)
        session = self.sessions.get(session_token)

        if (
            not session
            or not session.is_active
            or session.expired_at <= will_expire_at
            or session.deleted_at is not None
        ):
            return Error(detail="Session invalid", code=status.HTTP_401_UNAUTHORIZED)

        session.is_active = False
        return Message(detail="Sessions invalidated successfully")
