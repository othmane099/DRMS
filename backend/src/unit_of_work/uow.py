from collections.abc import Callable
from typing import Any, Protocol

from dependency_injector.wiring import Provide, inject
from sqlalchemy.ext.asyncio import AsyncSession

from auth.logged_histories.repository import (
    LoggedHistoryRepository,
    LoggedHistoryRepositoryImpl,
)
from auth.permissions.repository import PermissionRepository, PermissionRepositoryImpl
from auth.roles.repository import RoleRepository, RoleRepositoryImpl
from auth.sessions.repository import SessionRepository, SessionRepositoryImpl
from auth.users.repository import UserRepository, UserRepositoryImpl
from configuration.categories.repository import (
    CategoryRepository,
    CategoryRepositoryImpl,
)
from configuration.stages.repository import StageRepository, StageRepositoryImpl
from configuration.subcategories.repository import (
    SubcategoryRepository,
    SubcategoryRepositoryImpl,
)
from configuration.tags.repository import TagRepository, TagRepositoryImpl
from core.documents.repository import DocumentRepository, DocumentRepositoryImpl
from core.histories.repository import HistoryRepository, HistoryRepositoryImpl
from core.reminders.repository import ReminderRepository, ReminderRepositoryImpl


class UnitOfWork(Protocol):
    permission_repository: PermissionRepository
    role_repository: RoleRepository
    user_repository: UserRepository
    session_repository: SessionRepository
    logged_history_repository: LoggedHistoryRepository
    stage_repository: StageRepository
    category_repository: CategoryRepository
    subcategory_repository: SubcategoryRepository
    tag_repository: TagRepository
    document_repository: DocumentRepository
    reminder_repository: ReminderRepository
    history_repository: HistoryRepository

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class UnitOfWorkImpl(UnitOfWork):
    @inject
    def __init__(
        self,
        session_factory: Callable[[], Any] = Provide["DEFAULT_SESSION_FACTORY"],
    ):
        self.session_factory = session_factory()
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> UnitOfWork:
        self.session = self.session_factory
        self.permission_repository = PermissionRepositoryImpl(self.session)
        self.role_repository = RoleRepositoryImpl(self.session)
        self.user_repository = UserRepositoryImpl(self.session)
        self.session_repository = SessionRepositoryImpl(self.session)
        self.logged_history_repository = LoggedHistoryRepositoryImpl(self.session)
        self.stage_repository = StageRepositoryImpl(self.session)
        self.category_repository = CategoryRepositoryImpl(self.session)
        self.subcategory_repository = SubcategoryRepositoryImpl(self.session)
        self.tag_repository = TagRepositoryImpl(self.session)
        self.document_repository = DocumentRepositoryImpl(self.session)
        self.reminder_repository = ReminderRepositoryImpl(self.session)
        self.history_repository = HistoryRepositoryImpl(self.session)

        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any
    ) -> None:
        if self.session is not None:
            await self.session.aclose()

    async def commit(self) -> None:
        if self.session is not None:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session is not None:
            await self.session.rollback()
