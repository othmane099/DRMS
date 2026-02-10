import secrets
from datetime import datetime, timedelta
from uuid import uuid4

import pytz
from starlette import status

from auth.models import Session, User
from auth.schemas import LoginRequest, LoginResponse
from auth.sessions.fakes import FakeSessionService
from schemas import Error


class FakeAuthService:
    def __init__(self, session_service: FakeSessionService):
        self._users: dict[str, User] = {}
        self._passwords: dict[str, str] = {}
        self._session_service = session_service

    def add_user(
        self,
        username: str,
        password: str,
        is_active: bool = True,
        first_name: str = "",
        last_name: str = "",
    ) -> User:
        normalized = username.strip().lower()
        user = User(
            id=uuid4(),
            username=normalized,
            password=password,
            is_active=is_active,
            is_superuser=False,
            first_name=first_name,
            last_name=last_name,
            created_at=datetime.now(),
        )
        self._users[normalized] = user
        self._passwords[normalized] = password
        return user

    async def authenticate(
        self, body: LoginRequest, ip_address: str | None = None
    ) -> LoginResponse | Error:
        normalized = body.username.strip().lower()
        user = self._users.get(normalized)

        if not user or self._passwords.get(normalized) != body.password:
            return Error(
                detail="Invalid username or password",
                code=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Error(detail="Inactive user", code=status.HTTP_401_UNAUTHORIZED)

        token = secrets.token_urlsafe(32)
        session = Session(
            id=uuid4(),
            token=token,
            user_id=user.id,
            expired_at=datetime.now(pytz.utc) + timedelta(hours=24),
            is_active=True,
            created_at=datetime.now(pytz.utc),
        )
        self._session_service.sessions[token] = session
        return LoginResponse(
            token=session.token, user=user, expires_in=session.expires_in
        )
