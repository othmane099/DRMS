from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import UUID4

from auth.dependencies import CurrentUser
from core.reminders.schemas import (
    PaginatedReminderResponse,
    ReminderResponse,
    ReminderUpdate,
)
from core.reminders.service import ReminderService
from schemas import Error, Message

router = APIRouter(tags=["reminders"])


@router.get(
    "/reminders",
    response_model=PaginatedReminderResponse,
    description="Required permission: reminders.list | reminders.list_my",
)
@inject
async def get_all_reminders(
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, description="Number of items per page"),
    document_id: UUID4 | None = Query(None),
    reminder_service: ReminderService = Depends(Provide["reminder_service"]),
) -> PaginatedReminderResponse:
    result = await reminder_service.get_all_reminders_paginated(
        page=page,
        page_size=page_size,
        document_id=document_id,
        current_user=current_user,
    )

    if isinstance(result, Error):
        raise HTTPException(status_code=result.code, detail=result.detail)

    return result


@router.delete(
    "/reminders/{reminder_id}",
    response_model=Message,
    description="Required permission: reminders.delete | reminders.delete_my",
)
@inject
async def delete_reminder(
    reminder_id: UUID4,
    current_user: CurrentUser,
    reminder_service: ReminderService = Depends(Provide["reminder_service"]),
) -> Message:
    result = await reminder_service.delete_reminder(
        reminder_id=reminder_id,
        current_user=current_user,
    )

    if isinstance(result, Error):
        raise HTTPException(status_code=result.code, detail=result.detail)

    return result


@router.put(
    "/reminders/{reminder_id}",
    response_model=ReminderResponse,
    description="Required permission: reminders.update | reminders.update_my",
)
@inject
async def update_reminder(
    reminder_id: UUID4,
    reminder_update: ReminderUpdate,
    current_user: CurrentUser,
    reminder_service: ReminderService = Depends(Provide["reminder_service"]),
) -> ReminderResponse:
    result = await reminder_service.update_reminder(
        reminder_id=reminder_id,
        reminder_update=reminder_update,
        current_user=current_user,
    )

    if isinstance(result, Error):
        raise HTTPException(status_code=result.code, detail=result.detail)

    return ReminderResponse.model_validate(result)


@router.get(
    "/reminders/{reminder_id}",
    response_model=ReminderResponse,
    description="Required permission: reminders.view | reminders.view_my",
)
@inject
async def get_reminder(
    reminder_id: UUID4,
    current_user: CurrentUser,
    reminder_service: ReminderService = Depends(Provide["reminder_service"]),
) -> ReminderResponse:
    result = await reminder_service.get_reminder_by_id(
        reminder_id=reminder_id, current_user=current_user
    )

    if isinstance(result, Error):
        raise HTTPException(status_code=result.code, detail=result.detail)

    return ReminderResponse.model_validate(result)
