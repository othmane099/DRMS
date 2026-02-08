import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import require_permission
from auth.permissions.schemas import (
    PermissionResponse,
)
from auth.permissions.service import PermissionService
from schemas import Error

router = APIRouter(tags=["permissions"])

logger = logging.getLogger(__name__)


@router.get(
    "/permissions",
    response_model=list[PermissionResponse],
    dependencies=[Depends(require_permission("permissions.list"))],
    description="Required permission: permissions.list",
)
@inject
async def get_permissions(
    permission_service: PermissionService = Depends(Provide["permission_service"]),
) -> list[PermissionResponse]:
    response = await permission_service.get_all_permissions()
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response
