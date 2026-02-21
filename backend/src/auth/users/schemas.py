from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import UUID4, BaseModel, ConfigDict, EmailStr, Field

from auth.permissions.schemas import PermissionResponse
from auth.roles.schemas import RoleWithPermissionsResponse


class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"


class UserCreate(BaseModel):
    first_name: Annotated[str, Field(max_length=255)]
    last_name: Annotated[str, Field(max_length=255)]
    email: Annotated[EmailStr, Field(max_length=255)] | None = None
    phone: Annotated[str, Field(max_length=20)] | None = None
    username: Annotated[str, Field(max_length=50)]
    password: Annotated[str, Field(max_length=255)]
    is_active: bool = True
    role_id: UUID4 | None = None


class UserUpdate(BaseModel):
    first_name: Annotated[str, Field(max_length=255)]
    last_name: Annotated[str, Field(max_length=255)]
    email: Annotated[EmailStr, Field(max_length=255)] | None = None
    phone: Annotated[str, Field(max_length=20)] | None = None
    username: Annotated[str, Field(max_length=50)]
    is_active: bool = True
    role_id: UUID4 | None = None


class UserResponse(BaseModel):
    id: UUID4
    first_name: str
    last_name: str
    email: EmailStr | None
    phone: str | None
    username: str
    is_active: bool
    is_superuser: bool
    last_login: datetime | None = None
    role: RoleWithPermissionsResponse | None = None
    custom_permissions: list[PermissionResponse] | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaginatedUserResponse(BaseModel):
    data: list[UserResponse]
    current_page: int
    total_pages: int
    total_rows: int
    page_size: int
    has_next: bool
    has_previous: bool


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserRoleUpdate(BaseModel):
    role_id: UUID4 | None


class BulkUserAction(BaseModel):
    user_ids: list[UUID4]
    action: str
    parameters: dict | None = None


class BulkActionResponse(BaseModel):
    success_count: int
    failure_count: int
    details: list[str] | None = None


class UserPermissionsUpdate(BaseModel):
    permissions: list[str]


class PermissionBasicResponse(BaseModel):
    id: UUID4
    name: str
    code: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class UserPermissionsResponse(BaseModel):
    id: UUID4
    username: str
    role_permissions: list[PermissionBasicResponse]
    custom_permissions: list[PermissionBasicResponse]
    model_config = ConfigDict(from_attributes=True)


class UserBasicResponse(BaseModel):
    username: str
    model_config = ConfigDict(from_attributes=True)


class UserBasicIdResponse(BaseModel):
    id: UUID4
    username: str
    model_config = ConfigDict(from_attributes=True)
