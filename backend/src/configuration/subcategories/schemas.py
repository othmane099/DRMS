from datetime import datetime
from typing import Annotated

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator


class SubcategoryCreate(BaseModel):
    title: Annotated[str, Field(max_length=255)]
    category_id: UUID4

    @field_validator("title")
    @classmethod
    def lowercase_title(cls, v: str) -> str:
        return v.lower().strip()


class SubcategoryUpdate(SubcategoryCreate):
    pass


class SubcategoryResponse(BaseModel):
    id: UUID4
    title: str
    category_id: UUID4
    category_title: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SubcategoryBasicResponse(BaseModel):
    title: str
    model_config = ConfigDict(from_attributes=True)


class PaginatedSubcategoryResponse(BaseModel):
    data: list[SubcategoryResponse]
    current_page: int
    total_pages: int
    total_rows: int
    page_size: int
    has_next: bool
    has_previous: bool
