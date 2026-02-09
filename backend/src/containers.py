import os
import sys

from dependency_injector import containers, providers

from core.histories.service import HistoryServiceImpl
from core.reminders.service import ReminderServiceImpl

sys.path.append(f"{os.getcwd()}/src")
from auth.logged_histories.service import LoggedHistoryServiceImpl
from auth.permissions.service import PermissionServiceImpl
from auth.roles.service import RoleServiceImpl
from auth.service import AuthService
from auth.sessions.service import SessionServiceImpl
from auth.users.service import UserServiceImpl
from configuration.categories.service import CategoryServiceImpl
from configuration.stages.service import StageServiceImpl
from configuration.subcategories.service import SubcategoryServiceImpl
from configuration.tags.service import TagServiceImpl
from core.dashboard.service import DashboardServiceImpl
from core.documents.service import DocumentServiceImpl
from db import default_session_factory
from unit_of_work.uow import UnitOfWorkImpl


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=[
            "auth",
            "configuration",
            "core",
        ]
    )

    DEFAULT_SESSION_FACTORY = default_session_factory

    unit_of_work = providers.Factory(
        UnitOfWorkImpl, session_factory=DEFAULT_SESSION_FACTORY
    )
    permission_service = providers.Factory(
        PermissionServiceImpl,
        unit_of_work=unit_of_work,
    )
    user_service = providers.Factory(
        UserServiceImpl,
        unit_of_work=unit_of_work,
    )
    role_service = providers.Factory(
        RoleServiceImpl,
        unit_of_work=unit_of_work,
        permission_service=permission_service,
        user_service=user_service,
    )
    session_service = providers.Factory(
        SessionServiceImpl,
        unit_of_work=unit_of_work,
    )
    logged_history_service = providers.Factory(
        LoggedHistoryServiceImpl,
        unit_of_work=unit_of_work,
    )
    auth_service = providers.Factory(
        AuthService,
        unit_of_work=unit_of_work,
    )
    stage_service = providers.Factory(
        StageServiceImpl,
        unit_of_work=unit_of_work,
    )
    category_service = providers.Factory(
        CategoryServiceImpl,
        unit_of_work=unit_of_work,
    )
    subcategory_service = providers.Factory(
        SubcategoryServiceImpl,
        unit_of_work=unit_of_work,
    )
    tag_service = providers.Factory(
        TagServiceImpl,
        unit_of_work=unit_of_work,
    )
    document_service = providers.Factory(
        DocumentServiceImpl,
        unit_of_work=unit_of_work,
    )
    dashboard_service = providers.Factory(
        DashboardServiceImpl,
        unit_of_work=unit_of_work,
    )
    reminder_service = providers.Factory(
        ReminderServiceImpl,
        unit_of_work=unit_of_work,
    )
    history_service = providers.Factory(
        HistoryServiceImpl,
        unit_of_work=unit_of_work,
    )
