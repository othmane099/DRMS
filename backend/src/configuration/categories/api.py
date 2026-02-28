import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import UUID4

from auth.dependencies import require_any_permission, require_permission
from configuration.categories.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    CategoryWithSubcategoriesResponse,
    PaginatedCategoryResponse,
)
from configuration.categories.service import CategoryService
from schemas import Error, Message

router = APIRouter(tags=["categories"])

logger = logging.getLogger(__name__)


@router.get(
    "/categories",
    response_model=PaginatedCategoryResponse,
    dependencies=[
        Depends(
            require_any_permission(
                "categories.list", "documents.create"
            )
        )
    ],
    description="Required permission: categories.list | documents.create",
)
@inject
async def get_categories(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, description="Number of items per page"),
    search: str | None = Query(None, description="Search in category title"),
    category_service: CategoryService = Depends(Provide["category_service"]),
) -> PaginatedCategoryResponse:
    response = await category_service.get_all_categories_paginated(
        page=page, page_size=page_size, search=search
    )
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=201,
    dependencies=[Depends(require_permission("categories.create"))],
    description="Required permission: categories.create",
)
@inject
async def create_category(
    category_create: CategoryCreate,
    category_service: CategoryService = Depends(Provide["category_service"]),
) -> CategoryResponse:
    response = await category_service.create_category(category_create)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.get(
    "/categories/{category_id}",
    response_model=CategoryWithSubcategoriesResponse,
    dependencies=[Depends(require_permission("categories.view"))],
    description="Required permission: categories.view",
)
@inject
async def get_category(
    category_id: UUID4,
    category_service: CategoryService = Depends(Provide["category_service"]),
) -> CategoryWithSubcategoriesResponse:
    response = await category_service.get_category_by_id(category_id)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.put(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    dependencies=[Depends(require_permission("categories.update"))],
    description="Required permission: categories.update",
)
@inject
async def update_category(
    category_id: UUID4 = Path(..., description="Category ID"),
    category_update: CategoryUpdate = ...,
    category_service: CategoryService = Depends(Provide["category_service"]),
) -> CategoryResponse:
    response = await category_service.update_category(category_id, category_update)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.delete(
    "/categories/{category_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("categories.delete"))],
    description="Required permission: categories.delete",
)
@inject
async def delete_category(
    category_id: UUID4 = Path(..., description="Category ID"),
    category_service: CategoryService = Depends(Provide["category_service"]),
) -> Message:
    response = await category_service.delete_category(category_id)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response
