import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException
from pydantic import UUID4

from auth.dependencies import require_permission
from auth.roles.schemas import (
    AssignPermissionsRequest,
    RoleCreate,
    RoleResponse,
    RoleStatusUpdate,
    RoleUpdate,
    RoleWithPermissionsResponse,
)
from auth.roles.service import RoleService
from schemas import Error, Message

router = APIRouter(tags=["roles"])

logger = logging.getLogger(__name__)


@router.get(
    "/roles",
    response_model=list[RoleResponse],
    dependencies=[Depends(require_permission("roles.list"))],
    description="Required permission: roles.list",
)
@inject
async def get_roles(role_service: RoleService = Depends(Provide["role_service"])):
    response = await role_service.get_all_roles()
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.get(
    "/roles/{role_id}",
    response_model=RoleWithPermissionsResponse,
    dependencies=[Depends(require_permission("roles.view"))],
    description="Required permission: roles.view",
)
@inject
async def get_role(
    role_id: UUID4, role_service: RoleService = Depends(Provide["role_service"])
):
    response = await role_service.get_role_by_id(role_id)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.post(
    "/roles",
    response_model=RoleResponse,
    dependencies=[Depends(require_permission("roles.create"))],
    description="Required permission: roles.create",
)
@inject
async def create_role(
    role_create: RoleCreate,
    role_service: RoleService = Depends(Provide["role_service"]),
):
    response = await role_service.create_role(role_create)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.put(
    "/roles/{role_id}",
    response_model=RoleResponse,
    dependencies=[Depends(require_permission("roles.update"))],
    description="Required permission: roles.update",
)
@inject
async def update_role(
    role_id: UUID4,
    role_update: RoleUpdate,
    role_service: RoleService = Depends(Provide["role_service"]),
):
    response = await role_service.update_role(role_id, role_update)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.delete(
    "/roles/{role_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("roles.delete"))],
    description="Required permission: roles.delete",
)
@inject
async def delete_role(
    role_id: UUID4, role_service: RoleService = Depends(Provide["role_service"])
):
    response = await role_service.delete_role(role_id)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.patch(
    "/roles/{role_id}/status",
    response_model=RoleResponse,
    dependencies=[Depends(require_permission("roles.update"))],
    description="Required permission: roles.update",
)
@inject
async def update_role_status(
    role_id: UUID4,
    status_update: RoleStatusUpdate,
    role_service: RoleService = Depends(Provide["role_service"]),
):
    response = await role_service.update_role_status(role_id, status_update)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.post(
    "/roles/{role_id}/permissions",
    response_model=RoleWithPermissionsResponse,
    dependencies=[Depends(require_permission("roles.assign_permissions"))],
    description="Required permission: roles.assign_permissions",
)
@inject
async def assign_permissions_to_role(
    role_id: UUID4,
    request: AssignPermissionsRequest,
    role_service: RoleService = Depends(Provide["role_service"]),
):
    response = await role_service.assign_permissions(role_id, request)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response
