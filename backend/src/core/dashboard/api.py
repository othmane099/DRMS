import logging
from datetime import date

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from auth.dependencies import CurrentUser, get_current_user
from core.dashboard.schemas import DashboardResponse
from core.dashboard.service import DashboardService

router = APIRouter(tags=["dashboard"])

logger = logging.getLogger(__name__)


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    dependencies=[Depends(get_current_user)],
)
@inject
async def get_dashboard(
    current_user: CurrentUser,
    reminder_start_date: date | None = Query(default=None),
    reminder_end_date: date | None = Query(default=None),
    dashboard_service: DashboardService = Depends(Provide["dashboard_service"]),
) -> DashboardResponse:
    return await dashboard_service.get_dashboard(
        reminder_start_date=reminder_start_date,
        reminder_end_date=reminder_end_date,
        user_id=current_user.id,
    )
