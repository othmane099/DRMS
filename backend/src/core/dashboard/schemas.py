from datetime import date

from pydantic import UUID4, BaseModel


class DocumentByCategoryResponse(BaseModel):
    category: str
    count: int


class DocumentBySubcategoryResponse(BaseModel):
    subcategory: str
    count: int


class ReminderEventResponse(BaseModel):
    id: UUID4
    title: str
    start: date
    time: str


class DashboardResponse(BaseModel):
    total_user: int
    my_total_document: int
    total_document: int
    my_today_document: int
    today_document: int
    total_category: int
    my_total_reminder: int
    total_reminder: int
    my_today_reminder: int
    today_reminder: int
    document_by_category: list[DocumentByCategoryResponse]
    document_by_subcategory: list[DocumentBySubcategoryResponse]
    my_reminders: list[ReminderEventResponse]
    reminders: list[ReminderEventResponse]
