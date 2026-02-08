from datetime import datetime
from typing import Annotated

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator


class StageCreate(BaseModel):
    title: Annotated[str, Field(max_length=255)]
    color: Annotated[str, Field(min_length=7, max_length=7)]

    @field_validator("title")
    @classmethod
    def lowercase_title(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("color")
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        if not v.startswith("#"):
            raise ValueError("Color must start with #")
        hex_part = v[1:]
        if len(hex_part) != 6:
            raise ValueError("Color must be in format #RRGGBB")
        try:
            int(hex_part, 16)
        except ValueError:
            raise ValueError("Color must contain valid hexadecimal characters")
        return v.upper()


class StageUpdate(StageCreate):
    pass


class StageResponse(BaseModel):
    id: UUID4
    title: str
    color: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaginatedStageResponse(BaseModel):
    data: list[StageResponse]
    current_page: int
    total_pages: int
    total_rows: int
    page_size: int
    has_next: bool
    has_previous: bool


class StageBasicResponse(BaseModel):
    title: str
    color: str | None
    model_config = ConfigDict(from_attributes=True)
