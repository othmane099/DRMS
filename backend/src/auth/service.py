import logging
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from pydantic import UUID4
from starlette import status

from auth.logged_histories.schemas import LoggedHistoryCreate
from auth.models import LoggedHistoryType, Session
from auth.schemas import LoginRequest, LoginResponse
from auth.sessions.service import calculate_session_expiry, generate_session_token
from auth.users.schemas import UserResponse
from schemas import Error
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)


class AuthService(Protocol):
    async def authenticate(
        self, body: LoginRequest, ip_address: str | None = None
    ) -> Error | LoginResponse: ...


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def _verify_password(password: str, hashed_password: str) -> bool:
    return pbkdf2_sha256.verify(secret=password, hash=hashed_password)


async def _log_failed_login(
    uow: UnitOfWork,
    user_id: UUID | None,
    username: str,
    ip_address: str | None,
    reason: str,
) -> None:
    await uow.logged_history_repository.create_logged_history(
        LoggedHistoryCreate(
            user_id=user_id,
            ip=ip_address,
            date=datetime.now(tz=UTC),
            details={"username": username, "reason": reason},
            type=LoggedHistoryType.FAILED_LOGIN,
        )
    )


async def _log_successful_login(
    uow: UnitOfWork,
    user_id: UUID4,
    username: str,
    ip_address: str | None,
) -> None:
    await uow.logged_history_repository.create_logged_history(
        LoggedHistoryCreate(
            user_id=user_id,
            ip=ip_address,
            date=datetime.now(tz=UTC),
            details={"username": username},
            type=LoggedHistoryType.LOGIN,
        )
    )


async def _create_user_session(uow: UnitOfWork, user_id: UUID4) -> Session:
    session_token = generate_session_token()
    expired_at = calculate_session_expiry()
    return await uow.session_repository.create_session(
        user_id=user_id,
        session_token=session_token,
        expired_at=expired_at,
    )


class AuthServiceImpl(AuthService):
    @inject
    def __init__(self, unit_of_work: UnitOfWork = Provide["unit_of_work"]):
        self._unit_of_work = unit_of_work

    async def authenticate(
        self, body: LoginRequest, ip_address: str | None = None
    ) -> Error | LoginResponse:
        normalized_username = _normalize_username(body.username)
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
                or not _verify_password(body.password, str(user.password))
            ):
                logger.warning("Failed login attempt for username: %s", normalized_username)
                user_id = None if not user or isinstance(user, Error) else UUID(str(user.id))
                await _log_failed_login(
                    uow,
                    user_id,
                    body.username,
                    ip_address,
                    "invalid_username_or_password",
                )
                await uow.commit()
                return Error(
                    detail="Invalid username or password",
                    code=status.HTTP_401_UNAUTHORIZED,
                )

            if not user.is_active:
                logger.warning("Login attempt for inactive user: %s", normalized_username)
                await _log_failed_login(
                    uow, UUID(str(user.id)), body.username, ip_address, "inactive_user"
                )
                await uow.commit()
                return Error(detail="Inactive user", code=status.HTTP_401_UNAUTHORIZED)

            user.last_login = datetime.now(tz=UTC)
            user_uuid = UUID(str(user.id))
            session = await _create_user_session(uow, user_uuid)
            await _log_successful_login(uow, user_uuid, body.username, ip_address)
            await uow.commit()
            logger.info("User logged in successfully: %s (ID: %s)", user.username, user.id)
            return LoginResponse(
                token=str(session.token),
                user=UserResponse.model_validate(user),
                expires_in=session.expires_in,
            )
