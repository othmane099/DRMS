import logging
import secrets
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

import pytz
from dependency_injector.wiring import Provide, inject
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from starlette import status

from auth.models import Session
from schemas import Error, Message
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)


class SessionService(Protocol):
    async def generate_session_token(self) -> str: ...

    async def create_session(
        self,
        user_id: UUID,
        uow: UnitOfWork,
        hours_valid: int = 24,
    ) -> Session: ...

    async def get_active_session(self, session_token: str) -> Session | Error: ...

    async def invalidate_session(self, session_token: str) -> Message | Error: ...


class SessionServiceImpl(SessionService):
    @inject
    def __init__(
        self,
        unit_of_work: UnitOfWork = Provide["unit_of_work"],
    ):
        self._unit_of_work = unit_of_work

    async def generate_session_token(self) -> str:
        return secrets.token_urlsafe(32)

    async def create_session(
        self,
        user_id: UUID,
        uow: UnitOfWork,
        hours_valid: int = 24,
    ):
        session_token = await self.generate_session_token()
        expired_at = datetime.now(pytz.utc) + timedelta(hours=hours_valid)

        session = await uow.session_repository.create_session(
            user_id=user_id,
            session_token=session_token,
            expired_at=expired_at,
        )
        return session

    async def get_active_session(self, session_token: str):
        will_expire_at = datetime.now(pytz.utc)
        try:
            async with self._unit_of_work as uow:
                active_session = await uow.session_repository.get_active_session(
                    session_token, will_expire_at
                )
                if not active_session:
                    return Error(
                        detail="Session not found or expired",
                        code=status.HTTP_401_UNAUTHORIZED,
                    )
                return active_session
        except SQLAlchemyTimeoutError as exc:
            logger.error(
                "Database connection pool timeout while fetching session: %s", exc
            )
            return Error(
                detail="Database connection timed out. Please try again later.",
                code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    async def invalidate_session(self, session_token: str):
        logger.debug("Logout requested (session_key_suffix=%s)", session_token[-6:])
        will_expire_at = datetime.now(pytz.utc)
        async with self._unit_of_work as uow:
            active_session = await uow.session_repository.get_active_session(
                session_token, will_expire_at
            )
            if not active_session:
                logger.warning(
                    "Logout failed: invalid or expired session (token_suffix=%s)",
                    session_token[-6:],
                )
                return Error(
                    detail="Session invalid", code=status.HTTP_401_UNAUTHORIZED
                )

            active_session.is_active = False
            await uow.commit()
            logger.info(
                "Logout successful (user_id=%s, token_suffix=%s)",
                active_session.user_id,
                session_token[-6:],
            )
            return Message(detail="Sessions invalidated successfully")
