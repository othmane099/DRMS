import logging
from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, Header, HTTPException
from starlette import status

from auth.models import User
from auth.permissions.service import PermissionServiceImpl
from auth.roles.service import RoleService
from auth.sessions.service import SessionService
from schemas import Error

logger = logging.getLogger(__name__)


@inject
async def get_current_user(
    x_session_key: str = Header(
        alias="X-Session-Key", description="Session key for authentication"
    ),
    session_service: SessionService = Depends(Provide["session_service"]),
) -> User:
    session = await session_service.get_active_session(x_session_key)

    if isinstance(session, Error):
        logger.warning("Invalid or expired session token attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    user: User = session.user  # type: ignore
    if not user:
        logger.error(f"Session {x_session_key[:8]}... has no associated user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        logger.warning(
            f"Non-superuser {current_user.username} attempted superuser-only access"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Superuser required",
        )
    return current_user


def require_permission(*permission_codes: str) -> Callable[..., User]:
    @inject
    async def permission_checker(
        current_user: CurrentUser,
        permission_service: PermissionServiceImpl = Depends(
            Provide["permission_service"]
        ),
        role_service: RoleService = Depends(Provide["role_service"]),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        if current_user.role_id:
            role = await role_service.get_role_by_id(UUID(str(current_user.role_id)))
            if isinstance(role, Error):
                logger.warning(
                    f"User {current_user.username} has invalid role_id: {current_user.role_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Invalid role",
                )
            if not role.is_active:
                logger.warning(
                    f"User {current_user.username} has inactive role: {role.name}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Role is inactive",
                )

        user_permission_codes = set()

        if current_user.role_id:
            role_permissions = await permission_service.get_permissions_by_role_id(
                UUID(str(current_user.role_id))
            )
            user_permission_codes.update(
                perm.code for perm in role_permissions if perm.is_active
            )

        if current_user.custom_permissions:
            user_permission_codes.update(
                perm.code for perm in current_user.custom_permissions if perm.is_active
            )

        if not user_permission_codes:
            logger.warning(
                f"User {current_user.username} has no permissions (no role and no custom permissions)"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: No permissions assigned",
            )

        # Check if user has all required permissions
        for required_code in permission_codes:
            if required_code not in user_permission_codes:
                logger.warning(
                    f"User {current_user.username} lacks permission '{required_code}'. "
                    f"Has: {user_permission_codes}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: Missing permission '{required_code}'",
                )

        return current_user

    return permission_checker


def require_any_permission(*permission_codes: str) -> Callable[..., User]:
    @inject
    async def permission_checker(
        current_user: CurrentUser,
        permission_service: PermissionServiceImpl = Depends(
            Provide["permission_service"]
        ),
        role_service: RoleService = Depends(Provide["role_service"]),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        if current_user.role_id:
            role = await role_service.get_role_by_id(UUID(str(current_user.role_id)))
            if isinstance(role, Error):
                logger.warning(
                    f"User {current_user.username} has invalid role_id: {current_user.role_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Invalid role",
                )
            if not role.is_active:
                logger.warning(
                    f"User {current_user.username} has inactive role: {role.name}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Role is inactive",
                )

        user_permission_codes = set()

        if current_user.role_id:
            role_permissions = await permission_service.get_permissions_by_role_id(
                UUID(str(current_user.role_id))
            )
            user_permission_codes.update(
                perm.code for perm in role_permissions if perm.is_active
            )

        if current_user.custom_permissions:
            user_permission_codes.update(
                perm.code for perm in current_user.custom_permissions if perm.is_active
            )

        if not user_permission_codes:
            logger.warning(
                f"User {current_user.username} has no permissions (no role and no custom permissions)"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: No permissions assigned",
            )

        # Check if user has at least one of the required permissions
        if not user_permission_codes.intersection(permission_codes):
            logger.warning(
                f"User {current_user.username} lacks all of {set(permission_codes)}. "
                f"Has: {user_permission_codes}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires at least one of {set(permission_codes)}",
            )

        return current_user

    return permission_checker


RequireSuperuser = Annotated[User, Depends(require_superuser)]
