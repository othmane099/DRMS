import logging
from datetime import datetime

from dependency_injector.wiring import Provide, inject
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from starlette import status

from auth.logged_histories.schemas import LoggedHistoryCreate
from auth.logged_histories.service import LoggedHistoryService
from auth.models import LoggedHistoryType
from auth.schemas import LoginRequest, LoginResponse
from auth.sessions.service import SessionService
from auth.users.service import UserService
from schemas import Error
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)


class AuthService:
    @inject
    def __init__(
        self,
        unit_of_work: UnitOfWork = Provide["unit_of_work"],
        user_service: UserService = Provide["user_service"],
        session_service: SessionService = Provide["session_service"],
        logged_history_service: LoggedHistoryService = Provide[
            "logged_history_service"
        ],
    ):
        self._unit_of_work = unit_of_work
        self._user_service = user_service
        self._session_service = session_service
        self._logged_history_service = logged_history_service

    async def authenticate(self, body: LoginRequest, ip_address: str | None = None):
        normalized_username = body.username.strip().lower()
        logger.debug(
            "Login attempt for username=%s (normalized=%s)",
            body.username,
            normalized_username,
        )

        async with self._unit_of_work as uow:
            user = await self._user_service.get_user_by_username(
                normalized_username, uow
            )
            if isinstance(user, Error) or not pbkdf2_sha256.verify(
                secret=body.password, hash=user.password
            ):
                logger.warning(
                    "Failed login attempt for username: %s", normalized_username
                )

                user_id = None if isinstance(user, Error) else user.id
                await self._logged_history_service.create_logged_history(
                    LoggedHistoryCreate(
                        user_id=user_id,
                        ip=ip_address,
                        date=datetime.now(),
                        details={
                            "username": body.username,
                            "reason": "invalid_username_or_password",
                        },
                        type=LoggedHistoryType.FAILED_LOGIN,
                    ),
                    uow,
                )

                return Error(
                    detail="Invalid username or password",
                    code=status.HTTP_401_UNAUTHORIZED,
                )

            if not user.is_active:
                logger.warning(
                    "Login attempt for inactive user: %s", normalized_username
                )

                await self._logged_history_service.create_logged_history(
                    LoggedHistoryCreate(
                        user_id=user.id,
                        ip=ip_address,
                        date=datetime.now(),
                        details={"username": body.username, "reason": "inactive_user"},
                        type=LoggedHistoryType.FAILED_LOGIN,
                    ),
                    uow,
                )

                return Error(detail="Inactive user", code=status.HTTP_401_UNAUTHORIZED)

            user.last_login = datetime.now()
            session = await self._session_service.create_session(user.id, uow)
            await uow.commit()

            await self._logged_history_service.create_logged_history(
                LoggedHistoryCreate(
                    user_id=user.id,
                    ip=ip_address,
                    date=datetime.now(),
                    details={"username": body.username},
                    type=LoggedHistoryType.LOGIN,
                ),
                uow,
            )

            logger.info(f"User logged in successfully: {user.username} (ID: {user.id})")
            return LoginResponse(
                token=session.token, user=user, expires_in=session.expires_in
            )
