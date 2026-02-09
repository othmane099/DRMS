import logging
import secrets
from datetime import datetime, timedelta

import pytz
from dependency_injector.wiring import Provide, inject
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from pydantic import UUID4
from starlette import status

from auth.logged_histories.schemas import LoggedHistoryCreate
from auth.models import LoggedHistoryType
from auth.schemas import LoginRequest, LoginResponse
from schemas import Error
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)


class AuthService:
    @inject
    def __init__(self, unit_of_work: UnitOfWork = Provide["unit_of_work"]):
        self._unit_of_work = unit_of_work

    def _normalize_username(self, username: str) -> str:
        return username.strip().lower()

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        return pbkdf2_sha256.verify(secret=password, hash=hashed_password)

    async def _log_failed_login(
        self,
        uow: UnitOfWork,
        user_id: str | None,
        username: str,
        ip_address: str | None,
        reason: str,
    ) -> None:
        await uow.logged_history_repository.create_logged_history(
            LoggedHistoryCreate(
                user_id=user_id,
                ip=ip_address,
                date=datetime.now(),
                details={"username": username, "reason": reason},
                type=LoggedHistoryType.FAILED_LOGIN,
            )
        )

    async def _log_successful_login(
        self,
        uow: UnitOfWork,
        user_id: UUID4,
        username: str,
        ip_address: str | None,
    ) -> None:
        await uow.logged_history_repository.create_logged_history(
            LoggedHistoryCreate(
                user_id=user_id,
                ip=ip_address,
                date=datetime.now(),
                details={"username": username},
                type=LoggedHistoryType.LOGIN,
            )
        )

    def _generate_session_token(self) -> str:
        return secrets.token_urlsafe(32)

    def _calculate_session_expiry(self, hours: int = 24) -> datetime:
        return datetime.now(pytz.utc) + timedelta(hours=hours)

    async def _create_user_session(self, uow: UnitOfWork, user_id: UUID4):
        session_token = self._generate_session_token()
        expired_at = self._calculate_session_expiry()
        return await uow.session_repository.create_session(
            user_id=user_id,
            session_token=session_token,
            expired_at=expired_at,
        )

    async def authenticate(self, body: LoginRequest, ip_address: str | None = None):
        normalized_username = self._normalize_username(body.username)
        logger.debug(
            "Login attempt for username=%s (normalized=%s)",
            body.username,
            normalized_username,
        )

        async with self._unit_of_work as uow:
            user = await uow.user_repository.get_user_by_username(
                normalized_username, exclude_deleted=True
            )

            if (
                not user
                or isinstance(user, Error)
                or not self._verify_password(body.password, user.password)
            ):
                logger.warning(
                    "Failed login attempt for username: %s", normalized_username
                )
                user_id = None if not user or isinstance(user, Error) else user.id
                await self._log_failed_login(
                    uow,
                    user_id,
                    body.username,
                    ip_address,
                    "invalid_username_or_password",
                )
                return Error(
                    detail="Invalid username or password",
                    code=status.HTTP_401_UNAUTHORIZED,
                )

            if not user.is_active:
                logger.warning(
                    "Login attempt for inactive user: %s", normalized_username
                )
                await self._log_failed_login(
                    uow, user.id, body.username, ip_address, "inactive_user"
                )
                return Error(detail="Inactive user", code=status.HTTP_401_UNAUTHORIZED)

            user.last_login = datetime.now()
            session = await self._create_user_session(uow, user.id)
            await uow.commit()
            await self._log_successful_login(uow, user.id, body.username, ip_address)
            logger.info(f"User logged in successfully: {user.username} (ID: {user.id})")
            return LoginResponse(
                token=session.token, user=user, expires_in=session.expires_in
            )
