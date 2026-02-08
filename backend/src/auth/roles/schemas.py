from datetime import datetime
from typing import Annotated

from pydantic import UUID4, BaseModel, ConfigDict, Field

from auth.permissions.schemas import PermissionResponse


class RoleCreate(BaseModel):
    name: Annotated[str, Field(max_length=100)]
    description: Annotated[str, Field(max_length=255)] | None = None
    is_active: bool = True
    permissions: list[str] = []


class RoleUpdate(BaseModel):
    name: Annotated[str, Field(max_length=100)]
    description: Annotated[str, Field(max_length=255)] | None = None
    permissions: list[str] = []


class RoleResponse(BaseModel):
    id: UUID4
    name: str
    description: str | None
    is_active: bool
    permission_count: int | None = None
    user_count: int | None = None
    created_at: datetime
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class RoleWithPermissionsResponse(BaseModel):
    id: UUID4
    name: str
    description: str | None
    is_active: bool
    permissions: list[PermissionResponse]
    model_config = ConfigDict(from_attributes=True)


class PaginatedRoleResponse(BaseModel):
    data: list[RoleResponse]
    current_page: int
    total_pages: int
    total_rows: int
    page_size: int
    has_next: bool
    has_previous: bool


class RoleStatusUpdate(BaseModel):
    is_active: bool


class AssignPermissionsRequest(BaseModel):
    permission_ids: list[UUID4]
