from datetime import date, datetime, time
from typing import Annotated

from pydantic import UUID4, BaseModel, ConfigDict, Field

from auth.users.schemas import UserBasicResponse
from core.documents.schemas import DocumentBasicResponse


class PaginatedReminderResponse(BaseModel):
    data: list[ReminderResponse]
    current_page: int
    total_pages: int
    total_rows: int
    page_size: int
    has_next: bool
    has_previous: bool


class ReminderUpdate(BaseModel):
    date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    time: Annotated[str, Field(pattern=r"^\d{2}:\d{2}(:\d{2})?$")]
    subject: Annotated[str, Field(min_length=1, max_length=255)]
    message: Annotated[str, Field(min_length=1)]
    assign_user: Annotated[list[UUID4], Field(min_length=1)]


class ReminderCreate(BaseModel):
    date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    time: Annotated[str, Field(pattern=r"^\d{2}:\d{2}(:\d{2})?$")]
    subject: Annotated[str, Field(min_length=1, max_length=255)]
    message: Annotated[str, Field(min_length=1)]
    assign_user: Annotated[list[UUID4], Field(min_length=1)]


class ReminderResponse(BaseModel):
    id: UUID4
    document_id: UUID4
    date: date
    time: time
    subject: str
    message: str
    created_by: UUID4
    created_at: datetime
    updated_at: datetime | None
    creator: UserBasicResponse
    document: DocumentBasicResponse
    assigned_users: list[UserBasicResponse]
    model_config = ConfigDict(from_attributes=True)
