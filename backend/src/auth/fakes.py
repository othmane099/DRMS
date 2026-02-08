from passlib.handlers.pbkdf2 import pbkdf2_sha256
from starlette import status

from auth.logged_histories.fakes import FakeLoggedHistoryService
from auth.schemas import LoginRequest, LoginResponse
from auth.sessions.fakes import FakeSessionService
from auth.users.fakes import FakeUserService
from schemas import Error
from unit_of_work.fake_uow import FakeUnitOfWork


class FakeAuthService:
    def __init__(
        self,
        unit_of_work: FakeUnitOfWork | None = None,
        user_service: FakeUserService | None = None,
        session_service: FakeSessionService | None = None,
        logged_history_service: FakeLoggedHistoryService | None = None,
    ):
        self._unit_of_work = unit_of_work or FakeUnitOfWork()
        self._user_service = user_service or FakeUserService()
        self._session_service = session_service or FakeSessionService()
        self._logged_history_service = (
            logged_history_service or FakeLoggedHistoryService()
        )

    async def authenticate(
        self, body: LoginRequest, ip_address: str | None = None
    ) -> LoginResponse | Error:
        normalized_username = body.username.strip().lower()

        user = await self._user_service.get_user_by_username(normalized_username)
        if isinstance(user, Error):
            return Error(
                detail="Invalid username or password",
                code=status.HTTP_401_UNAUTHORIZED,
            )

        if not pbkdf2_sha256.verify(secret=body.password, hash=user.password):
            return Error(
                detail="Invalid username or password",
                code=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Error(detail="Inactive user", code=status.HTTP_401_UNAUTHORIZED)

        session = await self._session_service.create_session(
            user.id, self._unit_of_work
        )

        return LoginResponse(
            token=session.token, user=user, expires_in=session.expires_in
        )
