from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query

from auth.dependencies import CurrentUser
from core.histories.schemas import PaginatedDocumentHistoryResponse
from core.histories.service import HistoryService
from schemas import Error

router = APIRouter()


@router.get(
    "/histories",
    response_model=PaginatedDocumentHistoryResponse,
    description="Required permission: documents.history | documents.history_my",
)
@inject
async def get_document_histories(
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, description="Number of items per page"),
    search: str | None = Query(None, description="Search by action or description"),
    history_service: HistoryService = Depends(Provide["history_service"]),
) -> PaginatedDocumentHistoryResponse:
    response = await history_service.get_document_histories_paginated(
        page=page,
        page_size=page_size,
        search=search,
        current_user=current_user,
    )
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response
