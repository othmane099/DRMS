import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import UUID4

from auth.dependencies import CurrentUser, require_any_permission, require_permission
from auth.users.schemas import (
    BulkActionResponse,
    BulkUserAction,
    PaginatedUserResponse,
    UserBasicIdResponse,
    UserCreate,
    UserPermissionsResponse,
    UserPermissionsUpdate,
    UserResponse,
    UserResponseWithPrograms,
    UserRoleUpdate,
    UserStatus,
    UserStatusUpdate,
    UserUpdate,
)
from auth.users.service import UserService
from schemas import Error, Message

router = APIRouter(tags=["users"])

logger = logging.getLogger(__name__)


@router.get(
    "/users",
    response_model=PaginatedUserResponse,
    dependencies=[Depends(require_permission("users.list"))],
    description="Required permission: users.list | reminders.create | reminders.create_my",
)
@inject
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, description="Number of items per page"),
    role_id: UUID4 | None = Query(None, description="Filter by role ID"),
    search: str | None = Query(None, description="Search by name or email"),
    active: UserStatus | None = Query(None, description="Filter by active status"),
    user_service: UserService = Depends(Provide["user_service"]),
) -> PaginatedUserResponse:
    response = await user_service.get_all_users_paginated(
        page=page, page_size=page_size, role_id=role_id, search=search, active=active
    )
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.get(
    "/users/for-assignment",
    response_model=list[UserBasicIdResponse],
    dependencies=[
        Depends(
            require_any_permission(
                "documents.create",
                "documents.create_my",
                "reminders.create",
                "reminders.create_my",
            )
        )
    ],
    description="Get users for assignment (excludes current user and superusers). Required permission: documents.create | documents.create_my | reminders.create | reminders.create_my",
)
@inject
async def get_users_for_assignment(
    current_user: CurrentUser,
    user_service: UserService = Depends(Provide["user_service"]),
) -> list[UserBasicIdResponse]:
    users = await user_service.get_users_for_assignment(current_user.id)
    return [UserBasicIdResponse.model_validate(user) for user in users]


@router.get(
    "/users/{user_id}",
    response_model=UserResponseWithPrograms,
    dependencies=[Depends(require_permission("users.view"))],
    description="Required permission: users.view",
)
@inject
async def get_user(
    user_id: UUID4, user_service: UserService = Depends(Provide["user_service"])
) -> UserResponseWithPrograms:
    response = await user_service.get_user_by_id(user_id)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.post(
    "/users",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("users.create"))],
    description="Required permission: users.create",
)
@inject
async def create_user(
    user_create: UserCreate,
    user_service: UserService = Depends(Provide["user_service"]),
) -> UserResponse:
    response = await user_service.create_user(user_create)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("users.update"))],
    description="Required permission: users.update",
)
@inject
async def update_user(
    user_id: UUID4,
    user_update: UserUpdate,
    user_service: UserService = Depends(Provide["user_service"]),
) -> UserResponse:
    response = await user_service.update_user(user_id, user_update)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.delete(
    "/users/{user_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("users.delete"))],
    description="Required permission: users.delete",
)
@inject
async def delete_user(
    user_id: UUID4, user_service: UserService = Depends(Provide["user_service"])
) -> Message:
    response = await user_service.delete_user(user_id)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.put(
    "/users/{user_id}/status",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("users.update"))],
    description="Required permission: users.update",
)
@inject
async def update_user_status(
    user_id: UUID4,
    status_update: UserStatusUpdate,
    user_service: UserService = Depends(Provide["user_service"]),
) -> UserResponse:
    response = await user_service.update_user_status(user_id, status_update)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.put(
    "/users/{user_id}/role",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("users.update"))],
    description="Required permission: users.update",
)
@inject
async def update_user_role(
    user_id: UUID4,
    role_update: UserRoleUpdate,
    user_service: UserService = Depends(Provide["user_service"]),
) -> UserResponse:
    response = await user_service.update_user_role(user_id, role_update)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.post(
    "/users/bulk-action",
    response_model=BulkActionResponse,
    dependencies=[Depends(require_permission("users.update"))],
    description="Required permission: users.update",
)
@inject
async def bulk_user_action(
    bulk_action: BulkUserAction,
    user_service: UserService = Depends(Provide["user_service"]),
) -> BulkActionResponse:
    response = await user_service.bulk_action(bulk_action)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.get(
    "/users/{user_id}/permissions",
    response_model=UserPermissionsResponse,
    dependencies=[Depends(require_permission("users.view"))],
    description="Required permission: users.view",
)
@inject
async def get_user_permissions(
    user_id: UUID4,
    user_service: UserService = Depends(Provide["user_service"]),
) -> UserPermissionsResponse:
    response = await user_service.get_user_permissions(user_id)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.patch(
    "/users/{user_id}/permissions",
    response_model=UserPermissionsResponse,
    dependencies=[Depends(require_permission("users.update"))],
    description="Required permission: users.update",
)
@inject
async def update_user_permissions(
    user_id: UUID4,
    permissions_update: UserPermissionsUpdate,
    user_service: UserService = Depends(Provide["user_service"]),
) -> UserPermissionsResponse:
    response = await user_service.update_user_permissions(user_id, permissions_update)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response
