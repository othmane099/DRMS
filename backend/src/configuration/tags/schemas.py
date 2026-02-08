from datetime import datetime
from typing import Annotated

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator


class TagCreate(BaseModel):
    title: Annotated[str, Field(max_length=255)]

    @field_validator("title")
    @classmethod
    def lowercase_title(cls, v: str) -> str:
        return v.lower().strip()


class TagUpdate(TagCreate):
    pass


class TagBasicResponse(BaseModel):
    id: UUID4
    title: str
    model_config = ConfigDict(from_attributes=True)


class TagResponse(BaseModel):
    id: UUID4
    title: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaginatedTagResponse(BaseModel):
    data: list[TagResponse]
    current_page: int
    total_pages: int
    total_rows: int
    page_size: int
    has_next: bool
    has_previous: bool
