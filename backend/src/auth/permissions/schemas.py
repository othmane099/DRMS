from pydantic import UUID4, BaseModel, ConfigDict


class PermissionResponse(BaseModel):
    id: UUID4
    name: str
    code: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)
