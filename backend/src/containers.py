import os
import sys

import redis.asyncio as aioredis
from dependency_injector import containers, providers
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

sys.path.append(f"{os.getcwd()}/src")
from auth.logged_histories.service import LoggedHistoryServiceImpl
from auth.permissions.service import PermissionServiceImpl
from auth.roles.service import RoleServiceImpl
from auth.service import AuthServiceImpl
from auth.sessions.service import SessionServiceImpl
from auth.users.service import UserServiceImpl
from config import settings
from configuration.categories.service import CategoryServiceImpl
from configuration.stages.service import StageServiceImpl
from configuration.subcategories.service import SubcategoryServiceImpl
from configuration.tags.service import TagServiceImpl
from core.dashboard.service import DashboardServiceImpl
from core.documents.agents import DocumentAgentServiceImpl
from core.documents.chat_store import ChatStoreServiceImpl
from core.documents.rag import RagServiceImpl
from core.documents.service import DocumentServiceImpl
from core.histories.service import HistoryServiceImpl
from core.reminders.service import ReminderServiceImpl
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

    redis_client = providers.Singleton(
        aioredis.from_url,
        settings.REDIS_URL,
        decode_responses=True,
    )

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
        AuthServiceImpl,
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
    agent_service = providers.Factory(DocumentAgentServiceImpl)
    ollama_embeddings = providers.Singleton(
        OllamaEmbeddings,
        base_url=settings.OLLAMA_HOST,
        model=settings.OLLAMA_EMBED_MODEL,
    )
    rag_splitter = providers.Singleton(
        RecursiveCharacterTextSplitter,
        chunk_size=1_000,
        chunk_overlap=150,
    )
    rag_service = providers.Factory(
        RagServiceImpl,
        embeddings=ollama_embeddings,
        splitter=rag_splitter,
        qdrant_url=settings.QDRANT_URL,
    )
    chat_store_service = providers.Factory(
        ChatStoreServiceImpl,
        redis_client=redis_client,
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
