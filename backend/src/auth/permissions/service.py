import logging
from typing import Protocol

from dependency_injector.wiring import Provide, inject
from pydantic import UUID4

from auth.models import Permission
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)


class PermissionService(Protocol):
    async def get_all_permissions(self) -> list[Permission]: ...

    async def get_permissions_by_role_id(self, role_id: UUID4) -> list[Permission]: ...


class PermissionServiceImpl(PermissionService):
    @inject
    def __init__(self, unit_of_work: UnitOfWork = Provide["unit_of_work"]):
        self._unit_of_work = unit_of_work

    async def get_all_permissions(self) -> list[Permission]:
        logger.debug("Fetching all permissions")
        async with self._unit_of_work as uow:
            return await uow.permission_repository.get_all_permissions()

    async def get_permissions_by_role_id(self, role_id: UUID4) -> list[Permission]:
        logger.debug("Fetching permissions for role (role_id=%s)", role_id)
        async with self._unit_of_work as uow:
            return await uow.permission_repository.get_permissions_by_role_id(role_id)
