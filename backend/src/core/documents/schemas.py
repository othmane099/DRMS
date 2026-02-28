from datetime import date, datetime
from typing import Annotated

from pydantic import UUID4, BaseModel, ConfigDict, Field

from auth.users.schemas import UserBasicResponse
from configuration.categories.schemas import CategoryBasicResponse
from configuration.stages.schemas import StageBasicResponse
from configuration.subcategories.schemas import SubcategoryBasicResponse
from configuration.tags.schemas import TagBasicResponse


class DocumentCreate(BaseModel):
    name: Annotated[str, Field(max_length=255)]
    category_id: UUID4
    subcategory_id: UUID4
    stage_id: UUID4
    assigned_to: UUID4
    description: str | None = None
    tag_ids: list[UUID4] | None = None


class DocumentUpdate(BaseModel):
    name: Annotated[str, Field(max_length=255)]
    category_id: UUID4
    subcategory_id: UUID4
    stage_id: UUID4
    assigned_to: UUID4
    description: str | None = None
    tag_ids: list[UUID4] | None = None


class DocumentResponse(BaseModel):
    id: UUID4
    name: str
    category_id: UUID4
    subcategory_id: UUID4
    stage_id: UUID4
    assigned_to: UUID4
    description: str | None
    archive: bool
    created_by: UUID4
    stage: StageBasicResponse
    assigned_user: UserBasicResponse
    creator: UserBasicResponse
    category: CategoryBasicResponse
    subcategory: SubcategoryBasicResponse
    tags: list[TagBasicResponse]
    created_at: datetime
    updated_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class DocumentBasicResponse(BaseModel):
    name: str
    model_config = ConfigDict(from_attributes=True)


class VersionHistoryResponse(BaseModel):
    id: UUID4
    document_id: UUID4
    document_file: str
    version_number: int
    is_current: bool
    created_by: UUID4
    creator: UserBasicResponse
    summary: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DocumentFilterParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, description="Number of items per page")
    category_id: UUID4 | None = Field(None, description="Filter by category ID")
    stage_id: UUID4 | None = Field(None, description="Filter by stage ID")
    created_date: date | None = Field(None, description="Filter by creation date")
    archive: bool = Field(
        False, description="Filter by archive status (default: False)"
    )
    search: str | None = Field(
        None, description="Search in document name and description"
    )
    only_my: bool = Field(
        False, description="List only documents owned by the current user"
    )


class PaginatedDocumentResponse(BaseModel):
    data: list[DocumentResponse]
    current_page: int
    total_pages: int
    total_rows: int
    page_size: int
    has_next: bool
    has_previous: bool


class DocumentCommentCreate(BaseModel):
    comment: Annotated[str, Field(min_length=1)]


class DocumentCommentResponse(BaseModel):
    id: UUID4
    document_id: UUID4
    user_id: UUID4
    comment: str
    created_at: datetime
    updated_at: datetime | None
    user: UserBasicResponse
    model_config = ConfigDict(from_attributes=True)


class ShareDocumentCreate(BaseModel):
    user_ids: Annotated[list[UUID4], Field(min_length=1)]
    start_date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")] | None = None
    end_date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")] | None = None


class ShareDocumentResponse(BaseModel):
    id: UUID4
    document_id: UUID4
    user_id: UUID4
    start_date: date | None
    end_date: date | None
    created_at: datetime
    updated_at: datetime | None
    user: UserBasicResponse
    model_config = ConfigDict(from_attributes=True)


class ShareLinkCreate(BaseModel):
    expiration_date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")] | None = None
    password: str | None = None


class ShareLinkResponse(BaseModel):
    token: str


class ShareLinkAccessRequest(BaseModel):
    password: str | None = None


class DocumentSearchFilters(BaseModel):
    title_contains: str | None = None
    description_contains: str | None = None
    category: str | None = None
    subcategory: str | None = None
    stage: str | None = None
    assignee_name: str | None = None
    created_by_name: str | None = None
    tags: list[str] | None = None
    created_after: date | None = None
    created_before: date | None = None
    archived: bool | None = None
    limit: int = Field(default=20, ge=1, le=100)


class DocumentSearchRequest(BaseModel):
    message: Annotated[str, Field(min_length=1)]


class DocumentSearchResponse(BaseModel):
    message: str


class DocumentChatRequest(BaseModel):
    message: Annotated[str, Field(min_length=1)]


class DocumentChatResponse(BaseModel):
    message: str
