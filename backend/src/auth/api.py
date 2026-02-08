import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Header, HTTPException, Request

from auth.schemas import LoginRequest, LoginResponse
from auth.service import AuthService
from auth.sessions.service import SessionService
from schemas import Error

router = APIRouter(prefix="", tags=["auth"])

logger = logging.getLogger(__name__)


@router.post("/login", response_model=LoginResponse)
@inject
async def login(
    body: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(Provide["auth_service"]),
):
    client_ip = request.client.host if request.client else None
    response = await auth_service.authenticate(body, ip_address=client_ip)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response


@router.post("/logout")
@inject
async def logout(
    x_session_key: str = Header(
        alias="X-Session-Key", description="Session key for authentication"
    ),
    session_service: SessionService = Depends(Provide["session_service"]),
):
    response = await session_service.invalidate_session(x_session_key)
    if isinstance(response, Error):
        raise HTTPException(status_code=response.code, detail=response.detail)
    return response
