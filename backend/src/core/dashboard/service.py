import logging
from datetime import date
from typing import Protocol

from dependency_injector.wiring import Provide, inject
from pydantic import UUID4

from core.dashboard.schemas import (
    DashboardResponse,
    DocumentByCategoryResponse,
    DocumentBySubcategoryResponse,
    ReminderEventResponse,
)
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)


class DashboardService(Protocol):
    async def get_dashboard(
        self,
        reminder_start_date: date | None = None,
        reminder_end_date: date | None = None,
        user_id: UUID4 | None = None,
    ) -> DashboardResponse: ...


class DashboardServiceImpl(DashboardService):
    @inject
    def __init__(self, unit_of_work: UnitOfWork = Provide["unit_of_work"]):
        self._unit_of_work = unit_of_work

    async def get_dashboard(
        self,
        reminder_start_date: date | None = None,
        reminder_end_date: date | None = None,
        user_id: UUID4 | None = None,
    ) -> DashboardResponse:
        today = date.today()

        async with self._unit_of_work as uow:
            total_document = await uow.document_repository.count_documents()
            my_total_document = await uow.document_repository.count_documents(
                user_id=user_id
            )
            today_document = await uow.document_repository.count_documents(
                created_date=today
            )
            my_today_document = await uow.document_repository.count_documents(
                created_date=today, user_id=user_id
            )
            total_reminder = await uow.reminder_repository.count_reminders()
            my_total_reminder = await uow.reminder_repository.count_reminders(
                user_id=user_id
            )
            today_reminder = await uow.reminder_repository.count_reminders(
                reminder_date=today
            )
            my_today_reminder = await uow.reminder_repository.count_reminders(
                reminder_date=today, user_id=user_id
            )
            reminders = await uow.reminder_repository.get_all_reminders(
                start_date=reminder_start_date,
                end_date=reminder_end_date,
            )
            my_reminders = await uow.reminder_repository.get_all_reminders(
                start_date=reminder_start_date,
                end_date=reminder_end_date,
                user_id=user_id,
            )

            total_user = await uow.user_repository.count_users()
            total_category = await uow.category_repository.count_categories()
            docs_by_cat = await uow.document_repository.get_documents_by_category()
            docs_by_subcat = (
                await uow.document_repository.get_documents_by_subcategory()
            )

        return DashboardResponse(
            total_user=total_user,
            my_total_document=my_total_document,
            total_document=total_document,
            my_today_document=my_today_document,
            today_document=today_document,
            total_category=total_category,
            my_total_reminder=my_total_reminder,
            total_reminder=total_reminder,
            my_today_reminder=my_today_reminder,
            today_reminder=today_reminder,
            document_by_category=[
                DocumentByCategoryResponse(category=title, count=count)
                for title, count in docs_by_cat
            ],
            document_by_subcategory=[
                DocumentBySubcategoryResponse(subcategory=title, count=count)
                for title, count in docs_by_subcat
            ],
            reminders=[
                ReminderEventResponse(
                    id=r.id,
                    title=r.subject,
                    start=r.date,
                    time=r.time.strftime("%H:%M"),
                )
                for r in reminders
            ],
            my_reminders=[
                ReminderEventResponse(
                    id=r.id,
                    title=r.subject,
                    start=r.date,
                    time=r.time.strftime("%H:%M"),
                )
                for r in my_reminders
            ],
        )
