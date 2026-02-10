import logging
from datetime import datetime

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import UUID4

from auth.dependencies import require_permission
from auth.logged_histories.schemas import (
    PaginatedLoggedHistoryResponse,
)
from auth.logged_histories.service import LoggedHistoryService
from auth.models import LoggedHistoryType
from schemas import Error

router = APIRouter(tags=["logged-histories"])

logger = logging.getLogger(__name__)


@router.get(
    "/logged-history",
    response_model=PaginatedLoggedHistoryResponse,
    dependencies=[Depends(require_permission("logged_histories.view"))],
    description="Required permission: logged_histories.view",
)
@inject
async def get_logged_histories(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, description="Number of items per page"),
    user_id: UUID4 | None = Query(None, description="Filter by user ID"),
    type: LoggedHistoryType | None = Query(None, description="Filter by action type"),
    date_from: datetime | None = Query(None, description="Filter from date"),
    date_to: datetime | None = Query(None, description="Filter to date"),
    search: str | None = Query(None, description="Search in details"),
    logged_history_service: LoggedHistoryService = Depends(
        Provide["logged_history_service"]
    ),
) -> PaginatedLoggedHistoryResponse:
    response = await logged_history_service.get_all_logged_histories_paginated(
        page=page,
        page_size=page_size,
        user_id=user_id,
        type_filter=type,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response
