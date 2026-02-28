import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import UUID4

from auth.dependencies import require_any_permission, require_permission
from configuration.subcategories.schemas import (
    PaginatedSubcategoryResponse,
    SubcategoryCreate,
    SubcategoryResponse,
    SubcategoryUpdate,
)
from configuration.subcategories.service import SubcategoryService
from schemas import Error, Message

router = APIRouter(tags=["subcategories"])

logger = logging.getLogger(__name__)


@router.get(
    "/subcategories",
    response_model=PaginatedSubcategoryResponse,
    dependencies=[
        Depends(require_any_permission("subcategories.list", "documents.create"))
    ],
    description="Required permission: subcategories.list | documents.create",
)
@inject
async def get_subcategories(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, description="Number of items per page"),
    search: str | None = Query(None, description="Search in subcategory title"),
    category_id: UUID4 | None = Query(None, description="Filter by category"),
    subcategory_service: SubcategoryService = Depends(Provide["subcategory_service"]),
) -> PaginatedSubcategoryResponse:
    response = await subcategory_service.get_all_subcategories_paginated(
        page=page, page_size=page_size, search=search, category_id=category_id
    )
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.post(
    "/subcategories",
    response_model=SubcategoryResponse,
    status_code=201,
    dependencies=[Depends(require_permission("subcategories.create"))],
    description="Required permission: subcategories.create",
)
@inject
async def create_subcategory(
    subcategory_create: SubcategoryCreate,
    subcategory_service: SubcategoryService = Depends(Provide["subcategory_service"]),
) -> SubcategoryResponse:
    response = await subcategory_service.create_subcategory(subcategory_create)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.get(
    "/subcategories/{subcategory_id}",
    response_model=SubcategoryResponse,
    dependencies=[Depends(require_permission("subcategories.view"))],
    description="Required permission: subcategories.view",
)
@inject
async def get_subcategory(
    subcategory_id: UUID4 = Path(..., description="Subcategory ID"),
    subcategory_service: SubcategoryService = Depends(Provide["subcategory_service"]),
) -> SubcategoryResponse:
    response = await subcategory_service.get_subcategory_by_id(subcategory_id)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.put(
    "/subcategories/{subcategory_id}",
    response_model=SubcategoryResponse,
    dependencies=[Depends(require_permission("subcategories.update"))],
    description="Required permission: subcategories.update",
)
@inject
async def update_subcategory(
    subcategory_id: UUID4,
    subcategory_update: SubcategoryUpdate,
    subcategory_service: SubcategoryService = Depends(Provide["subcategory_service"]),
) -> SubcategoryResponse:
    response = await subcategory_service.update_subcategory(
        subcategory_id, subcategory_update
    )
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.delete(
    "/subcategories/{subcategory_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("subcategories.delete"))],
    description="Required permission: subcategories.delete",
)
@inject
async def delete_subcategory(
    subcategory_id: UUID4,
    subcategory_service: SubcategoryService = Depends(Provide["subcategory_service"]),
) -> Message:
    response = await subcategory_service.delete_subcategory(subcategory_id)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response
