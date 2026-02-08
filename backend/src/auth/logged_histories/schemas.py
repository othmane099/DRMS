from datetime import datetime
from typing import Annotated, Any

from pydantic import UUID4, BaseModel, ConfigDict, Field

from auth.models import LoggedHistoryType


class LoggedHistoryCreate(BaseModel):
    user_id: UUID4 | None = None
    ip: Annotated[str, Field(max_length=255)] | None = None
    date: datetime | None = None
    details: dict[str, Any] | None = None
    type: LoggedHistoryType | None = None


class LoggedHistoryResponse(BaseModel):
    id: UUID4
    user_id: UUID4 | None
    user_name: str | None = None
    ip: str | None
    date: datetime | None
    details: dict[str, Any] | None
    type: LoggedHistoryType | None
    model_config = ConfigDict(from_attributes=True)


class PaginatedLoggedHistoryResponse(BaseModel):
    data: list[LoggedHistoryResponse]
    current_page: int
    total_pages: int
    total_rows: int
    page_size: int
    has_next: bool
    has_previous: bool
