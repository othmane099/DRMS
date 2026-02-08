import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import UUID4

from auth.dependencies import require_any_permission, require_permission
from configuration.stages.schemas import (
    PaginatedStageResponse,
    StageCreate,
    StageResponse,
    StageUpdate,
)
from configuration.stages.service import StageService
from schemas import Error, Message

router = APIRouter(tags=["stages"])

logger = logging.getLogger(__name__)


@router.get(
    "/stages",
    response_model=PaginatedStageResponse,
    dependencies=[
        Depends(
            require_any_permission(
                "stages.list", "documents.create", "documents.create_my"
            )
        )
    ],
    description="Required permission: stages.list | documents.create | documents.create_my",
)
@inject
async def get_stages(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, description="Number of items per page"),
    search: str | None = Query(None, description="Search in stage title"),
    stage_service: StageService = Depends(Provide["stage_service"]),
) -> PaginatedStageResponse:
    response = await stage_service.get_all_stages_paginated(
        page=page, page_size=page_size, search=search
    )
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.post(
    "/stages",
    response_model=StageResponse,
    status_code=201,
    dependencies=[Depends(require_permission("stages.create"))],
    description="Required permission: stages.create",
)
@inject
async def create_stage(
    stage_create: StageCreate,
    stage_service: StageService = Depends(Provide["stage_service"]),
) -> StageResponse:
    response = await stage_service.create_stage(stage_create)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return StageResponse.model_validate(response)


@router.get(
    "/stages/{stage_id}",
    response_model=StageResponse,
    dependencies=[Depends(require_permission("stages.view"))],
    description="Required permission: stages.view",
)
@inject
async def get_stage(
    stage_id: UUID4 = Path(..., description="Stage ID"),
    stage_service: StageService = Depends(Provide["stage_service"]),
) -> StageResponse:
    response = await stage_service.get_stage_by_id(stage_id)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return StageResponse.model_validate(response)


@router.put(
    "/stages/{stage_id}",
    response_model=StageResponse,
    dependencies=[Depends(require_permission("stages.update"))],
    description="Required permission: stages.update",
)
@inject
async def update_stage(
    stage_id: UUID4 = Path(..., description="Stage ID"),
    stage_update: StageUpdate = ...,
    stage_service: StageService = Depends(Provide["stage_service"]),
) -> StageResponse:
    response = await stage_service.update_stage(stage_id, stage_update)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return StageResponse.model_validate(response)


@router.delete(
    "/stages/{stage_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("stages.delete"))],
    description="Required permission: stages.delete",
)
@inject
async def delete_stage(
    stage_id: UUID4 = Path(..., description="Stage ID"),
    stage_service: StageService = Depends(Provide["stage_service"]),
) -> Message:
    response = await stage_service.delete_stage(stage_id)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response
