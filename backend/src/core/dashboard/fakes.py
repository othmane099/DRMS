from datetime import date
from uuid import UUID

from core.dashboard.schemas import (
    DashboardResponse,
    DocumentByCategoryResponse,
    DocumentBySubcategoryResponse,
    ReminderEventResponse,
)


class FakeDashboardService:
    def __init__(self) -> None:
        self.total_user: int = 0
        self.my_total_document: int = 0
        self.total_document: int = 0
        self.my_today_document: int = 0
        self.today_document: int = 0
        self.total_category: int = 0
        self.my_total_reminder: int = 0
        self.total_reminder: int = 0
        self.my_today_reminder: int = 0
        self.today_reminder: int = 0
        self.document_by_category: list[tuple[str, int]] = []
        self.document_by_subcategory: list[tuple[str, int]] = []
        self.my_reminders: list[tuple[UUID, str, date, str]] = []
        self.reminders: list[tuple[UUID, str, date, str]] = []

    async def get_dashboard(
        self,
        reminder_start_date: date | None = None,
        reminder_end_date: date | None = None,
        user_id: UUID | None = None,
    ) -> DashboardResponse:
        return DashboardResponse(
            total_user=self.total_user,
            my_total_document=self.my_total_document,
            total_document=self.total_document,
            my_today_document=self.my_today_document,
            today_document=self.today_document,
            total_category=self.total_category,
            my_total_reminder=self.my_total_reminder,
            total_reminder=self.total_reminder,
            my_today_reminder=self.my_today_reminder,
            today_reminder=self.today_reminder,
            document_by_category=[
                DocumentByCategoryResponse(category=cat, count=count)
                for cat, count in self.document_by_category
            ],
            document_by_subcategory=[
                DocumentBySubcategoryResponse(subcategory=sub, count=count)
                for sub, count in self.document_by_subcategory
            ],
            my_reminders=[
                ReminderEventResponse(id=id_, title=title, start=start, time=time_)
                for id_, title, start, time_ in self.my_reminders
            ],
            reminders=[
                ReminderEventResponse(id=id_, title=title, start=start, time=time_)
                for id_, title, start, time_ in self.reminders
            ],
        )
