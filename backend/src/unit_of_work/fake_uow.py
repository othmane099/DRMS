from typing import Any

from auth.logged_histories.fakes import FakeLoggedHistoryRepository
from auth.permissions.fakes import FakePermissionRepository
from auth.roles.fakes import FakeRoleRepository
from auth.sessions.fakes import FakeSessionRepository
from auth.users.fakes import FakeUserRepository
from configuration.categories.fakes import FakeCategoryRepository
from configuration.stages.fakes import FakeStageRepository
from configuration.subcategories.fakes import FakeSubcategoryRepository
from configuration.tags.fakes import FakeTagRepository
from core.documents.fakes import FakeDocumentRepository
from core.histories.fakes import FakeHistoryRepository
from core.reminders.fakes import FakeReminderRepository
from unit_of_work.uow import UnitOfWork


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.session = None
        self.permission_repository = FakePermissionRepository()
        self.role_repository = FakeRoleRepository()
        self.session_repository = FakeSessionRepository()
        self.user_repository = FakeUserRepository()
        self.logged_history_repository = FakeLoggedHistoryRepository()
        self.stage_repository = FakeStageRepository()
        self.category_repository = FakeCategoryRepository()
        self.subcategory_repository = FakeSubcategoryRepository()
        self.tag_repository = FakeTagRepository()
        self.document_repository = FakeDocumentRepository()
        self.reminder_repository = FakeReminderRepository()
        self.history_repository = FakeHistoryRepository()
        # Connect reminder repository to document repository so it can access documents
        self.reminder_repository.documents = self.document_repository.documents

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any
    ) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass
