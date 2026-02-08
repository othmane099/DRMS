from pydantic import BaseModel

from auth.users.schemas import UserResponse


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserResponse
    expires_in: int
