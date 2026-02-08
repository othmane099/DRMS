from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query

from auth.dependencies import CurrentUser, require_permission
from core.histories.schemas import PaginatedDocumentHistoryResponse
from core.histories.service import HistoryService
from schemas import Error

router = APIRouter()


@router.get(
    "/histories",
    response_model=PaginatedDocumentHistoryResponse,
    dependencies=[Depends(require_permission("documents.history"))],
    description="Required permission: documents.history",
)
@inject
async def get_document_histories(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, description="Number of items per page"),
    search: str | None = Query(None, description="Search by action or description"),
    history_service: HistoryService = Depends(Provide["history_service"]),
) -> PaginatedDocumentHistoryResponse:
    response = await history_service.get_document_histories_paginated(
        page=page,
        page_size=page_size,
        search=search,
    )
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.get(
    "/histories/me",
    response_model=PaginatedDocumentHistoryResponse,
    dependencies=[Depends(require_permission("documents.history_my"))],
    description="Required permission: documents.history_my",
)
@inject
async def get_my_document_histories(
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, description="Number of items per page"),
    search: str | None = Query(None, description="Search by action or description"),
    history_service: HistoryService = Depends(Provide["history_service"]),
) -> PaginatedDocumentHistoryResponse:
    response = await history_service.get_document_histories_paginated(
        page=page, page_size=page_size, search=search, user_id=current_user.id
    )
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response
