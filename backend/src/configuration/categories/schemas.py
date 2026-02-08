from datetime import datetime
from typing import Annotated

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator

from configuration.subcategories.schemas import (
    SubcategoryBasicResponse,
)


class CategoryCreate(BaseModel):
    title: Annotated[str, Field(max_length=255)]

    @field_validator("title")
    @classmethod
    def lowercase_title(cls, v: str) -> str:
        return v.lower().strip()


class CategoryUpdate(CategoryCreate):
    pass


class CategoryResponse(BaseModel):
    id: UUID4
    title: str
    created_at: datetime
    subcategory_count: int
    model_config = ConfigDict(from_attributes=True)


class CategoryBasicResponse(BaseModel):
    title: str
    model_config = ConfigDict(from_attributes=True)


class CategoryWithSubcategoriesResponse(BaseModel):
    id: UUID4
    title: str
    subcategory_count: int
    subcategories: list[SubcategoryBasicResponse]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaginatedCategoryResponse(BaseModel):
    data: list[CategoryResponse]
    current_page: int
    total_pages: int
    total_rows: int
    page_size: int
    has_next: bool
    has_previous: bool
