from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict

from auth.users.schemas import UserBasicResponse
from core.documents.schemas import DocumentBasicResponse


class DocumentHistoryResponse(BaseModel):
    id: UUID4
    document_id: UUID4 | None
    action: str
    description: str
    created_by: UUID4
    created_at: datetime
    document: DocumentBasicResponse | None
    creator: UserBasicResponse
    model_config = ConfigDict(from_attributes=True)


class PaginatedDocumentHistoryResponse(BaseModel):
    data: list[DocumentHistoryResponse]
    current_page: int
    total_pages: int
    total_rows: int
    page_size: int
    has_next: bool
    has_previous: bool
