import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import UUID4

from auth.dependencies import require_any_permission, require_permission
from configuration.tags.schemas import (
    PaginatedTagResponse,
    TagCreate,
    TagResponse,
    TagUpdate,
)
from configuration.tags.service import TagService
from schemas import Error, Message

router = APIRouter(tags=["tags"])

logger = logging.getLogger(__name__)


@router.get(
    "/tags",
    response_model=PaginatedTagResponse,
    dependencies=[
        Depends(
            require_any_permission(
                "tags.list", "documents.create", "documents.create_my"
            )
        )
    ],
    description="Required permission: tags.list | documents.create | documents.create_my",
)
@inject
async def get_tags(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, description="Number of items per page"),
    search: str | None = Query(None, description="Search in tag title"),
    tag_service: TagService = Depends(Provide["tag_service"]),
) -> PaginatedTagResponse:
    response = await tag_service.get_all_tags_paginated(
        page=page, page_size=page_size, search=search
    )
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.post(
    "/tags",
    response_model=TagResponse,
    status_code=201,
    dependencies=[Depends(require_permission("tags.create"))],
    description="Required permission: tags.create",
)
@inject
async def create_tag(
    tag_create: TagCreate,
    tag_service: TagService = Depends(Provide["tag_service"]),
) -> TagResponse:
    response = await tag_service.create_tag(tag_create)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return TagResponse.model_validate(response)


@router.get(
    "/tags/{tag_id}",
    response_model=TagResponse,
    dependencies=[Depends(require_permission("tags.view"))],
    description="Required permission: tags.view",
)
@inject
async def get_tag(
    tag_id: UUID4,
    tag_service: TagService = Depends(Provide["tag_service"]),
) -> TagResponse:
    response = await tag_service.get_tag_by_id(tag_id)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return TagResponse.model_validate(response)


@router.put(
    "/tags/{tag_id}",
    response_model=TagResponse,
    dependencies=[Depends(require_permission("tags.update"))],
    description="Required permission: tags.update",
)
@inject
async def update_tag(
    tag_id: UUID4,
    tag_update: TagUpdate = ...,
    tag_service: TagService = Depends(Provide["tag_service"]),
) -> TagResponse:
    response = await tag_service.update_tag(tag_id, tag_update)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return TagResponse.model_validate(response)


@router.delete(
    "/tags/{tag_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("tags.delete"))],
    description="Required permission: tags.delete",
)
@inject
async def delete_tag(
    tag_id: UUID4 = Path(..., description="Tag ID"),
    tag_service: TagService = Depends(Provide["tag_service"]),
) -> Message:
    response = await tag_service.delete_tag(tag_id)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response
