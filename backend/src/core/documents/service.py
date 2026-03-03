import json
import logging
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import date, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from dependency_injector.wiring import Provide, inject
from fastapi import BackgroundTasks, UploadFile
from pydantic import UUID4
from starlette import status

from auth.models import User
from auth.permissions.service import PermissionService
from auth.roles.service import RoleService
from config import settings
from core.documents.agents import DocumentAgentService
from core.documents.chat_store import ChatStoreService
from core.documents.rag import RagService
from core.documents.schemas import (
    DocumentCommentCreate,
    DocumentCreate,
    DocumentFilterParams,
    DocumentResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentUpdate,
    PaginatedDocumentResponse,
    ShareDocumentCreate,
    ShareLinkCreate,
)
from core.documents.text_extractor import extract_text
from core.models import (
    Document,
    DocumentComment,
    ShareDocument,
    VersionHistory,
)
from schemas import Error, Message
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(settings.UPLOAD_DIR)


@inject
async def _permission_checker(
    user: User,
    *permission_codes,
    permission_service: PermissionService = Provide["permission_service"],
    role_service: RoleService = Provide["role_service"],
) -> set[str] | None | Error:
    if user.is_superuser:
        return None

    user_permission_codes: set[str] = set()

    if user.role_id:
        role = await role_service.get_role_by_id(UUID(str(user.role_id)))
        if isinstance(role, Error):
            logger.warning(
                "User %s has invalid role (role_id=%s)", user.username, user.role_id
            )
            return Error(
                detail="Access denied: Invalid role", code=status.HTTP_403_FORBIDDEN
            )
        if not role.is_active:
            logger.warning("User %s has inactive role (role_id=%s)")
            return Error(
                detail="Access denied: Invalid role", code=status.HTTP_403_FORBIDDEN
            )
        role_permissions = await permission_service.get_permissions_by_role_id(
            UUID(str(user.role_id))
        )
        user_permission_codes.update(p.code for p in role_permissions if p.is_active)

    if user.custom_permissions:
        user_permission_codes.update(
            p.code for p in user.custom_permissions if p.is_active
        )

    if not user_permission_codes:
        logger.warning(
            f"User {user.username} has no permissions and no custom permissions"
        )
        return Error(
            code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Invalid permission",
        )
    intersected_permissions = user_permission_codes.intersection(permission_codes)
    if not intersected_permissions:
        logger.warning(
            f"User {user.username} lacks all of {set(permission_codes)}. "
            f"Has: {user_permission_codes}"
        )
        return Error(
            code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Invalid permission",
        )
    return intersected_permissions


@inject
async def _run_document_summary(
    version_id: UUID,
    document_name: str,
    document_file: str,
    unit_of_work: UnitOfWork = Provide["unit_of_work"],
    agent_service: DocumentAgentService = Provide["agent_service"],
) -> None:
    logger.info(
        "Summary task started (version_id=%s, document=%r)", version_id, document_name
    )
    try:
        logger.debug("Summary task: extracting text from %s", document_file)
        text = await extract_text(document_file)
        if not text:
            logger.info(
                "Summary task: skipped — no extractable text (version_id=%s, file=%s)",
                version_id,
                document_file,
            )
            return

        logger.debug(
            "Summary task: generating summary (%d chars) for %r",
            len(text),
            document_name,
        )
        summary = await agent_service.generate_summary(text, document_name)

        async with unit_of_work as uow:
            await uow.document_repository.update_version_summary(version_id, summary)
            await uow.commit()

        logger.info(
            "Summary task completed (version_id=%s, document=%r, summary_len=%d)",
            version_id,
            document_name,
            len(summary),
        )
    except Exception:
        logger.exception(
            "Summary task failed (version_id=%s, document=%r)",
            version_id,
            document_name,
        )


@inject
async def _run_document_embedding(
    version_id: UUID,
    document_file: str,
    rag_service: RagService = Provide["rag_service"],
) -> None:
    logger.info("Embedding task started (version_id=%s)", version_id)
    try:
        await rag_service.build_vectorstore(str(version_id), document_file)
        logger.info("Embedding task completed (version_id=%s)", version_id)
    except Exception:
        logger.exception("Embedding task failed (version_id=%s)", version_id)


ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "txt",
    "jpg",
    "jpeg",
    "png",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class DocumentService(Protocol):
    async def get_all_documents_paginated(
        self,
        filters: DocumentFilterParams,
        current_user: User,
    ) -> PaginatedDocumentResponse | Error: ...

    async def create_document(
        self,
        document_create: DocumentCreate,
        document_file: UploadFile,
        current_user: User,
        background_tasks: BackgroundTasks | None = None,
    ) -> Document | Error: ...

    async def update_document(
        self,
        document_id: UUID4,
        document_update: DocumentUpdate,
        current_user: User,
    ) -> Document | Error: ...

    async def delete_document(
        self, document_id: UUID4, current_user: User
    ) -> Message | Error: ...

    async def get_document_by_id(
        self, document_id: UUID4, current_user: User
    ) -> Document | Error: ...

    async def get_document_file_path(
        self,
        document_id: UUID4,
        current_user: User | None = None,
        full_permission: str = "documents.download",
        my_permission: str = "documents.download_my",
    ) -> str | Error: ...

    async def get_version_history(
        self, document_id: UUID4, current_user: User
    ) -> list[VersionHistory] | Error: ...

    async def create_new_version(
        self,
        document_id: UUID4,
        document_file: UploadFile,
        current_user: User,
        background_tasks: BackgroundTasks | None = None,
    ) -> VersionHistory | Error: ...

    async def get_version_file_path(
        self,
        document_id: UUID4,
        version_id: UUID4,
        current_user: User | None = None,
        full_permission: str = "documents.download_version",
        my_permission: str = "documents.download_version_my",
    ) -> str | Error: ...

    async def archive_document(
        self, document_id: UUID4, current_user: User
    ) -> Document | Error: ...

    async def create_comment(
        self,
        document_id: UUID4,
        comment_create: DocumentCommentCreate,
        current_user: User,
    ) -> DocumentComment | Error: ...

    async def get_document_comments(
        self, document_id: UUID4, current_user: User | None = None
    ) -> list[DocumentComment] | Error: ...

    async def share_document(
        self,
        document_id: UUID4,
        share_data: ShareDocumentCreate,
        current_user: User,
    ) -> list[ShareDocument] | Error: ...

    async def get_shared_users(
        self,
        document_id: UUID4,
        current_user: User | None = None,
    ) -> list[ShareDocument] | Error: ...

    async def get_document_users(
        self,
        document_id: UUID4,
        current_user: User,
    ) -> list[User] | Error: ...

    async def delete_share_document(
        self,
        document_id: UUID4,
        share_id: UUID4,
        current_user: User,
    ) -> Message | Error: ...

    async def generate_share_link(
        self,
        document_id: UUID4,
        share_link_create: ShareLinkCreate,
        current_user: User,
    ) -> str | Error: ...

    async def validate_share_link(
        self,
        token: str,
        password: str | None = None,
    ) -> UUID4 | Error: ...

    async def search_documents(
        self, request: DocumentSearchRequest, current_user: User | None = None
    ) -> DocumentSearchResponse | Error: ...

    async def chat_with_document_version(
        self,
        document_id: UUID4,
        version_id: UUID4,
        user_message: str,
        current_user: User | None = None,
    ) -> str | Error: ...


class DocumentServiceImpl(DocumentService):
    @inject
    def __init__(
        self,
        unit_of_work: UnitOfWork = Provide["unit_of_work"],
        agent_service: DocumentAgentService = Provide["agent_service"],
        rag_service: RagService = Provide["rag_service"],
        chat_store_service: ChatStoreService = Provide["chat_store_service"],
    ):
        self._unit_of_work = unit_of_work
        self._agent_service = agent_service
        self._rag_service = rag_service
        self._chat_store_service = chat_store_service

    async def get_all_documents_paginated(
        self,
        filters: DocumentFilterParams,
        current_user: User,
    ) -> PaginatedDocumentResponse | Error:
        result = await _permission_checker(
            current_user, "documents.list", "documents.list_my"
        )
        if isinstance(result, Error):
            return result

        can_list_all = result is None or "documents.list" in result
        user_id = current_user.id if (not can_list_all or filters.only_my) else None

        logger.debug(
            "Fetching documents (page=%s, page_size=%s, category_id=%s, "
            "stage_id=%s, created_date=%s, archive=%s, search=%s, user_id=%s)",
            filters.page,
            filters.page_size,
            filters.category_id,
            filters.stage_id,
            filters.created_date,
            filters.archive,
            filters.search,
            user_id,
        )

        skip = (filters.page - 1) * filters.page_size
        limit = filters.page_size

        async with self._unit_of_work as uow:
            documents = await uow.document_repository.get_documents_paginated(
                skip=skip,
                limit=limit,
                category_id=filters.category_id,
                stage_id=filters.stage_id,
                created_date=filters.created_date,
                archive=filters.archive,
                user_id=user_id,
                search=filters.search,
            )
            total_rows = await uow.document_repository.count_documents(
                category_id=filters.category_id,
                stage_id=filters.stage_id,
                created_date=filters.created_date,
                archive=filters.archive,
                user_id=user_id,
                search=filters.search,
            )

        total_pages = (total_rows + filters.page_size - 1) // filters.page_size

        logger.info(
            "Documents fetched (page=%s, page_size=%s, total_rows=%s, total_pages=%s)",
            filters.page,
            filters.page_size,
            total_rows,
            total_pages,
        )
        return PaginatedDocumentResponse(
            data=[DocumentResponse.model_validate(doc) for doc in documents],
            current_page=filters.page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=filters.page_size,
            has_next=filters.page < total_pages,
            has_previous=filters.page > 1,
        )

    async def create_document(
        self,
        document_create: DocumentCreate,
        document_file: UploadFile,
        current_user: User,
        background_tasks: BackgroundTasks | None = None,
    ) -> Document | Error:
        result = await _permission_checker(current_user, "documents.create")
        if isinstance(result, Error):
            return result

        current_user_id = current_user.id
        logger.info("Creating document (name=%s)", document_create.name)

        file_validation_error = await self._validate_file(document_file)
        if file_validation_error:
            return file_validation_error

        async with self._unit_of_work as uow:
            existing_document = await uow.document_repository.get_document_by_name(
                document_create.name
            )
            if existing_document:
                logger.warning(
                    "Document creation rejected: name already exists (name=%s)",
                    document_create.name,
                )
                return Error(
                    detail="Document name already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

            category = await uow.category_repository.get_category_by_id(
                document_create.category_id
            )
            if not category:
                logger.warning(
                    "Document creation rejected: category not found (category_id=%s)",
                    document_create.category_id,
                )
                return Error(
                    detail="Category not found", code=status.HTTP_404_NOT_FOUND
                )

            subcategory = await uow.subcategory_repository.get_subcategory_by_id(
                document_create.subcategory_id
            )
            if not subcategory:
                logger.warning(
                    "Document creation rejected: subcategory not found (subcategory_id=%s)",
                    document_create.subcategory_id,
                )
                return Error(
                    detail="Subcategory not found", code=status.HTTP_404_NOT_FOUND
                )

            stage = await uow.stage_repository.get_stage_by_id(document_create.stage_id)
            if not stage:
                logger.warning(
                    "Document creation rejected: stage not found (stage_id=%s)",
                    document_create.stage_id,
                )
                return Error(detail="Stage not found", code=status.HTTP_404_NOT_FOUND)

            assigned_user = await uow.user_repository.get_user_by_id(
                document_create.assigned_to
            )
            if not assigned_user:
                logger.warning(
                    "Document creation rejected: assigned user not found (user_id=%s)",
                    document_create.assigned_to,
                )
                return Error(
                    detail="Assigned user not found", code=status.HTTP_404_NOT_FOUND
                )

            # Validate tag IDs if provided
            if document_create.tag_ids:
                for tag_id in document_create.tag_ids:
                    tag = await uow.tag_repository.get_tag_by_id(tag_id)
                    if not tag:
                        logger.warning(
                            "Document creation rejected: tag not found (tag_id=%s)",
                            tag_id,
                        )
                        return Error(
                            detail=f"Tag not found: {tag_id}",
                            code=status.HTTP_404_NOT_FOUND,
                        )

            document = await uow.document_repository.create_document(
                document_create, current_user_id
            )

            # Create version history first to get version_id
            version = await uow.document_repository.create_version_history(
                document_id=document.id,
                document_file="",  # Placeholder, will be updated after file save
                version_number=1,
                created_by=current_user_id,
            )

            try:
                file_path = await self._save_file(
                    document_file, version.id, document.name
                )
            except Exception as e:
                logger.error("File upload failed: %s", str(e))
                await uow.rollback()
                return Error(
                    detail=f"File upload failed: {str(e)}",
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Update version with actual file path
            await uow.document_repository.update_version_file_path(
                version.id, file_path
            )

            description = f"New document '{document.name}' created"
            await uow.history_repository.create_document_history(
                document_id=document.id,
                action="Document Create",
                description=description,
                created_by=current_user_id,
            )

            await uow.commit()

            version_id = version.id
            doc_name = document.name
            doc_file = file_path

            created_document = await uow.document_repository.get_document_by_id(
                document.id
            )

        if background_tasks is not None:
            background_tasks.add_task(
                _run_document_summary, version_id, doc_name, doc_file
            )
            background_tasks.add_task(_run_document_embedding, version_id, doc_file)

        logger.info(
            "Document created successfully (id=%s, name=%s)",
            created_document.id,
            created_document.name,
        )
        return created_document

    async def update_document(
        self,
        document_id: UUID4,
        document_update: DocumentUpdate,
        current_user: User,
    ) -> Document | Error:
        result = await _permission_checker(
            current_user, "documents.update", "documents.update_my"
        )
        if isinstance(result, Error):
            return result

        can_update_all = result is None or "documents.update" in result
        user_id = None if can_update_all else current_user.id
        current_user_id = current_user.id

        logger.info("Updating document (id=%s)", document_id)

        async with self._unit_of_work as uow:
            existing_document = await uow.document_repository.get_document_by_id(
                document_id, user_id=user_id
            )
            if not existing_document:
                logger.warning(
                    "Document update rejected: document not found (id=%s)", document_id
                )
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            if (
                existing_document.created_by != current_user_id
                and existing_document.assigned_to != current_user_id
            ):
                logger.warning(
                    "Document update rejected: user is neither the creator nor the "
                    "assigned_to (id=%s, user=%s, creator=%s)",
                    document_id,
                    current_user_id,
                    existing_document.created_by,
                )
                return Error(
                    detail="Only the document creator can update the document",
                    code=status.HTTP_403_FORBIDDEN,
                )

            # Check if name is being changed and if so, check for duplicate
            if existing_document.name != document_update.name:
                name_exists = await uow.document_repository.get_document_by_name(
                    document_update.name
                )
                if name_exists:
                    logger.warning(
                        "Document update rejected: name already exists (name=%s)",
                        document_update.name,
                    )
                    return Error(
                        detail="Document name already exists",
                        code=status.HTTP_400_BAD_REQUEST,
                    )

            category = await uow.category_repository.get_category_by_id(
                document_update.category_id
            )
            if not category:
                logger.warning(
                    "Document update rejected: category not found (category_id=%s)",
                    document_update.category_id,
                )
                return Error(
                    detail="Category not found", code=status.HTTP_404_NOT_FOUND
                )

            subcategory = await uow.subcategory_repository.get_subcategory_by_id(
                document_update.subcategory_id
            )
            if not subcategory:
                logger.warning(
                    "Document update rejected: subcategory not found (subcategory_id=%s)",
                    document_update.subcategory_id,
                )
                return Error(
                    detail="Subcategory not found", code=status.HTTP_404_NOT_FOUND
                )

            stage = await uow.stage_repository.get_stage_by_id(document_update.stage_id)
            if not stage:
                logger.warning(
                    "Document update rejected: stage not found (stage_id=%s)",
                    document_update.stage_id,
                )
                return Error(detail="Stage not found", code=status.HTTP_404_NOT_FOUND)

            assigned_user = await uow.user_repository.get_user_by_id(
                document_update.assigned_to
            )
            if not assigned_user:
                logger.warning(
                    "Document update rejected: assigned user not found (user_id=%s)",
                    document_update.assigned_to,
                )
                return Error(
                    detail="Assigned user not found", code=status.HTTP_404_NOT_FOUND
                )

            # Validate tag IDs if provided
            if document_update.tag_ids:
                for tag_id in document_update.tag_ids:
                    tag = await uow.tag_repository.get_tag_by_id(tag_id)
                    if not tag:
                        logger.warning(
                            "Document update rejected: tag not found (tag_id=%s)",
                            tag_id,
                        )
                        return Error(
                            detail=f"Tag not found: {tag_id}",
                            code=status.HTTP_404_NOT_FOUND,
                        )

            changed_fields = []
            if existing_document.name != document_update.name:
                changed_fields.append(
                    f"name: '{existing_document.name}' → '{document_update.name}'"
                )
            if str(existing_document.category_id) != str(document_update.category_id):
                changed_fields.append("category")
            if str(existing_document.subcategory_id) != str(
                document_update.subcategory_id
            ):
                changed_fields.append("subcategory")
            if str(existing_document.stage_id) != str(document_update.stage_id):
                changed_fields.append("stage")
            if str(existing_document.assigned_to) != str(document_update.assigned_to):
                changed_fields.append("assigned user")
            if existing_document.description != document_update.description:
                changed_fields.append("description")
            existing_tag_ids = {str(t.id) for t in (existing_document.tags or [])}
            new_tag_ids = {str(t) for t in (document_update.tag_ids or [])}
            if existing_tag_ids != new_tag_ids:
                changed_fields.append("tags")

            document = await uow.document_repository.update_document(
                document_id, document_update
            )

            fields_summary = (
                ", ".join(changed_fields) if changed_fields else "no changes"
            )
            description = (
                f"Document '{document.name}' updated — changed: {fields_summary}"
            )
            await uow.history_repository.create_document_history(
                document_id=document.id,
                action="Document Update",
                description=description,
                created_by=current_user_id,
            )

            await uow.commit()

            updated_document = await uow.document_repository.get_document_by_id(
                document.id
            )

        logger.info(
            "Document updated successfully (id=%s, name=%s)",
            updated_document.id,
            updated_document.name,
        )
        return updated_document

    async def delete_document(
        self, document_id: UUID4, current_user: User
    ) -> Message | Error:
        result = await _permission_checker(
            current_user, "documents.delete", "documents.delete_my"
        )
        if isinstance(result, Error):
            return result

        can_delete_all = result is None or "documents.delete" in result
        user_id = None if can_delete_all else current_user.id
        current_user_id = current_user.id

        logger.info("Deleting document (id=%s)", document_id)

        async with self._unit_of_work as uow:
            document = await uow.document_repository.get_document_by_id(
                document_id, user_id=user_id
            )
            if not document:
                logger.warning(
                    "Document deletion rejected: document not found (id=%s)",
                    document_id,
                )
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            # Only the document creator can delete the document
            if document.created_by != current_user_id:
                logger.warning(
                    "Document deletion rejected: user is not the creator (id=%s, user=%s, creator=%s)",
                    document_id,
                    current_user_id,
                    document.created_by,
                )
                return Error(
                    detail="Only the document creator can delete the document",
                    code=status.HTTP_403_FORBIDDEN,
                )

            # Create history entry before deletion
            description = f"Document '{document.name}' deleted"
            await uow.history_repository.create_document_history(
                document_id=document.id,
                action="Document Delete",
                description=description,
                created_by=current_user_id,
            )

            # Get all version histories to delete associated files
            version_histories = await uow.document_repository.get_version_histories(
                document_id
            )

            # Delete physical files
            for version in version_histories:
                if version.document_file:
                    try:
                        file_path = Path(version.document_file)
                        if file_path.exists():
                            file_path.unlink()
                            logger.debug("Deleted file: %s", version.document_file)
                    except Exception as e:
                        logger.error(
                            "Failed to delete file %s: %s",
                            version.document_file,
                            str(e),
                        )

            # Delete version histories
            await uow.document_repository.delete_version_histories(document_id)

            # Delete document
            await uow.document_repository.delete_document(document_id)

            await uow.commit()

        logger.info("Document deleted successfully (id=%s)", document_id)
        return Message(detail="Document deleted successfully")

    async def get_document_by_id(
        self, document_id: UUID4, current_user: User
    ) -> Document | Error:
        result = await _permission_checker(
            current_user, "documents.view", "documents.view_my"
        )
        if isinstance(result, Error):
            return result

        can_view_all = result is None or "documents.view" in result
        user_id = None if can_view_all else current_user.id

        logger.info("Fetching document (id=%s)", document_id)

        async with self._unit_of_work as uow:
            document = await uow.document_repository.get_document_by_id(
                document_id, user_id=user_id
            )
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

        logger.info("Document fetched successfully (id=%s)", document_id)
        return document

    async def get_document_file_path(
        self,
        document_id: UUID4,
        current_user: User | None = None,
        full_permission: str = "documents.download",
        my_permission: str = "documents.download_my",
    ) -> str | Error:
        logger.info("Fetching document file path (id=%s)", document_id)

        user_id: UUID4 | None = None
        if current_user is not None:
            result = await _permission_checker(
                current_user, full_permission, my_permission
            )
            if isinstance(result, Error):
                return result
            can_access_all = result is None or full_permission in result
            user_id = None if can_access_all else current_user.id

        async with self._unit_of_work as uow:
            document = await uow.document_repository.get_document_by_id(
                document_id, user_id=user_id
            )
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            current_version = await uow.document_repository.get_current_version(
                document_id
            )
            if not current_version:
                logger.warning(
                    "No file version found for document (id=%s)", document_id
                )
                return Error(
                    detail="Document file not found", code=status.HTTP_404_NOT_FOUND
                )

        logger.info(
            "Document file path fetched successfully (id=%s, path=%s)",
            document_id,
            current_version.document_file,
        )
        return current_version.document_file

    async def get_version_history(
        self, document_id: UUID4, current_user: User
    ) -> list[VersionHistory] | Error:
        logger.info("Fetching version history (document_id=%s)", document_id)

        result = await _permission_checker(
            current_user, "documents.view_version", "documents.view_version_my"
        )
        if isinstance(result, Error):
            return result
        can_view_all = result is None or "documents.view_version" in result
        user_id = None if can_view_all else current_user.id

        async with self._unit_of_work as uow:
            document = await uow.document_repository.get_document_by_id(
                document_id, user_id=user_id
            )
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            versions = await uow.document_repository.get_version_histories(document_id)

        logger.info(
            "Version history fetched successfully (document_id=%s, count=%d)",
            document_id,
            len(versions),
        )
        return versions

    async def create_new_version(
        self,
        document_id: UUID4,
        document_file: UploadFile,
        current_user: User,
        background_tasks: BackgroundTasks | None = None,
    ) -> VersionHistory | Error:
        logger.info("Creating new version (document_id=%s)", document_id)

        result = await _permission_checker(
            current_user, "documents.create_version", "documents.create_version_my"
        )
        if isinstance(result, Error):
            return result
        can_create_all = result is None or "documents.create_version" in result
        user_id = None if can_create_all else current_user.id
        current_user_id = current_user.id

        file_validation_error = await self._validate_file(document_file)
        if file_validation_error:
            return file_validation_error

        async with self._unit_of_work as uow:
            document = await uow.document_repository.get_document_by_id(
                document_id, user_id=user_id
            )
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            # Only the document creator can create new versions
            if document.created_by != current_user_id:
                logger.warning(
                    "Version creation rejected: user is not the creator (id=%s, user=%s, creator=%s)",
                    document_id,
                    current_user_id,
                    document.created_by,
                )
                return Error(
                    detail="Only the document creator can create new versions",
                    code=status.HTTP_403_FORBIDDEN,
                )

            # Get existing versions to determine next version number
            existing_versions = await uow.document_repository.get_version_histories(
                document_id
            )
            next_version_number = len(existing_versions) + 1

            # Create new version history first to get version_id (this will set is_current=True and others to False)
            version = await uow.document_repository.create_version_history(
                document_id=document.id,
                document_file="",  # Placeholder, will be updated after file save
                version_number=next_version_number,
                created_by=current_user_id,
            )

            # Save the new file using version_id
            try:
                file_path = await self._save_file(
                    document_file, version.id, document.name
                )
            except Exception as e:
                logger.error("File upload failed: %s", str(e))
                await uow.rollback()
                return Error(
                    detail=f"File upload failed: {str(e)}",
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Update version with actual file path
            await uow.document_repository.update_version_file_path(
                version.id, file_path
            )

            # Get user for history description
            # Create document history entry
            description = f"New version uploaded for '{document.name}'"
            await uow.history_repository.create_document_history(
                document_id=document.id,
                action="New Version",
                description=description,
                created_by=current_user_id,
            )

            version_id = version.id
            doc_name = document.name
            doc_file = file_path

            await uow.commit()

        if background_tasks is not None:
            background_tasks.add_task(
                _run_document_summary, version_id, doc_name, doc_file
            )
            background_tasks.add_task(_run_document_embedding, version_id, doc_file)

        logger.info(
            "New version created successfully (document_id=%s, version=%d)",
            document_id,
            next_version_number,
        )
        return version

    async def get_version_file_path(
        self,
        document_id: UUID4,
        version_id: UUID4,
        current_user: User | None = None,
        full_permission: str = "documents.download_version",
        my_permission: str = "documents.download_version_my",
    ) -> str | Error:
        logger.info(
            "Fetching version file path (document_id=%s, version_id=%s)",
            document_id,
            version_id,
        )

        user_id: UUID4 | None = None
        if current_user is not None:
            result = await _permission_checker(
                current_user,
                full_permission,
                my_permission,
            )
            if isinstance(result, Error):
                return result
            can_access_all = result is None or full_permission in result
            user_id = None if can_access_all else current_user.id

        async with self._unit_of_work as uow:
            document = await uow.document_repository.get_document_by_id(
                document_id, user_id=user_id
            )
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            versions = await uow.document_repository.get_version_histories(document_id)
            version = next((v for v in versions if v.id == version_id), None)

            if not version:
                logger.warning(
                    "Version not found (document_id=%s, version_id=%s)",
                    document_id,
                    version_id,
                )
                return Error(detail="Version not found", code=status.HTTP_404_NOT_FOUND)

        logger.info(
            "Version file path fetched successfully (version_id=%s, path=%s)",
            version_id,
            version.document_file,
        )
        return version.document_file

    async def archive_document(
        self, document_id: UUID4, current_user: User
    ) -> Document | Error:
        result = await _permission_checker(
            current_user, "documents.archive", "documents.archive_my"
        )
        if isinstance(result, Error):
            return result

        can_archive_all = result is None or "documents.archive" in result
        user_id = None if can_archive_all else current_user.id
        current_user_id = current_user.id

        logger.info("Archiving document (id=%s)", document_id)

        async with self._unit_of_work as uow:
            document = await uow.document_repository.get_document_by_id(
                document_id, user_id=user_id
            )
            if not document:
                logger.warning(
                    "Document archiving rejected: document not found (id=%s)",
                    document_id,
                )
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            # Only the document creator can archive/unarchive the document
            if document.created_by != current_user_id:
                logger.warning(
                    "Document archiving rejected: user is not the creator (id=%s, user=%s, creator=%s)",
                    document_id,
                    current_user_id,
                    document.created_by,
                )
                return Error(
                    detail="Only the document creator can archive the document",
                    code=status.HTTP_403_FORBIDDEN,
                )

            archive_status = not document.archive
            await uow.document_repository.archive_document(document_id, archive_status)

            action = "Document Archive" if archive_status else "Document Unarchive"
            description = f"Document '{document.name}' {'archived' if archive_status else 'unarchived'}"
            await uow.history_repository.create_document_history(
                document_id=document.id,
                action=action,
                description=description,
                created_by=current_user_id,
            )

            await uow.commit()

            updated_document = await uow.document_repository.get_document_by_id(
                document.id
            )

        logger.info(
            "Document %s successfully (id=%s)",
            "archived" if archive_status else "unarchived",
            document_id,
        )
        return updated_document

    async def create_comment(
        self,
        document_id: UUID4,
        comment_create: DocumentCommentCreate,
        current_user: User,
    ) -> DocumentComment | Error:
        logger.info("Creating comment for document (document_id=%s)", document_id)

        result = await _permission_checker(
            current_user, "comments.create", "comments.create_my"
        )
        if isinstance(result, Error):
            return result
        can_create_all = result is None or "comments.create" in result
        user_id = None if can_create_all else current_user.id

        async with self._unit_of_work as uow:
            # Verify document exists
            document = await uow.document_repository.get_document_by_id(
                document_id, user_id=user_id
            )
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            # Create comment
            comment = await uow.document_repository.create_comment(
                document_id=document_id,
                user_id=current_user.id,
                comment=comment_create.comment,
            )

            # Create document history entry
            description = f"Comment created for '{document.name}'"
            await uow.history_repository.create_document_history(
                document_id=document.id,
                action="Comment Create",
                description=description,
                created_by=current_user.id,
            )

            await uow.commit()

        logger.info("Comment created successfully (document_id=%s)", document_id)
        return comment

    async def get_document_comments(
        self, document_id: UUID4, current_user: User | None = None
    ) -> list[DocumentComment] | Error:
        logger.info("Fetching comments for document (document_id=%s)", document_id)

        user_id: UUID4 | None = None
        if current_user is not None:
            result = await _permission_checker(
                current_user, "comments.list", "comments.list_my"
            )
            if isinstance(result, Error):
                return result
            can_list_all = result is None or "comments.list" in result
            user_id = None if can_list_all else current_user.id

        async with self._unit_of_work as uow:
            # Verify document exists
            document = await uow.document_repository.get_document_by_id(
                document_id, user_id=user_id
            )
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            # Get comments ordered by created_at ascending (oldest first, newest last)
            comments = await uow.document_repository.get_comments(document_id)

        logger.info(
            "Comments fetched successfully (document_id=%s, count=%d)",
            document_id,
            len(comments),
        )
        return comments

    async def share_document(
        self,
        document_id: UUID4,
        share_data: ShareDocumentCreate,
        current_user: User,
    ) -> list[ShareDocument] | Error:
        logger.info("Sharing document (document_id=%s)", document_id)

        result = await _permission_checker(
            current_user, "documents.share", "documents.share_my"
        )
        if isinstance(result, Error):
            return result
        can_share_all = result is None or "documents.share" in result
        scope_user_id = None if can_share_all else current_user.id

        # Validate date range if both dates are provided
        if share_data.start_date and share_data.end_date:
            from datetime import datetime

            start = datetime.strptime(share_data.start_date, "%Y-%m-%d").date()
            end = datetime.strptime(share_data.end_date, "%Y-%m-%d").date()
            if start > end:
                return Error(
                    detail="Start date must be before end date",
                    code=status.HTTP_400_BAD_REQUEST,
                )

        async with self._unit_of_work as uow:
            # Verify document exists
            document = await uow.document_repository.get_document_by_id(
                document_id, user_id=scope_user_id
            )
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            # Only the document creator can share the document
            if document.created_by != current_user.id:
                logger.warning(
                    "Document sharing rejected: user is not the creator (id=%s, user=%s, creator=%s)",
                    document_id,
                    current_user.id,
                    document.created_by,
                )
                return Error(
                    detail="Only the document creator can share the document",
                    code=status.HTTP_403_FORBIDDEN,
                )

            # Parse dates
            start_date = None
            end_date = None
            if share_data.start_date:
                from datetime import datetime

                start_date = datetime.strptime(share_data.start_date, "%Y-%m-%d").date()
            if share_data.end_date:
                from datetime import datetime

                end_date = datetime.strptime(share_data.end_date, "%Y-%m-%d").date()

            # Share with each user
            shared_list = []
            shared_usernames = []
            for share_user_id in share_data.user_ids:
                # Verify user exists
                user = await uow.user_repository.get_user_by_id(share_user_id)
                if not user:
                    logger.warning("User not found (user_id=%s)", share_user_id)
                    return Error(
                        detail=f"User not found: {share_user_id}",
                        code=status.HTTP_404_NOT_FOUND,
                    )

                # Check if already shared with this user
                existing_share = await uow.document_repository.check_existing_share(
                    document_id, share_user_id
                )
                if existing_share:
                    logger.warning(
                        "Document already shared with user (document_id=%s, user_id=%s)",
                        document_id,
                        share_user_id,
                    )
                    continue

                # Create share
                share = await uow.document_repository.share_document(
                    document_id=document_id,
                    user_id=share_user_id,
                    start_date=start_date,
                    end_date=end_date,
                )
                shared_list.append(share)
                shared_usernames.append(user.username)

            # Create document history entry
            user_names = ", ".join(shared_usernames) if shared_usernames else "none"
            description = f"Document '{document.name}' shared with users: {user_names}"
            await uow.history_repository.create_document_history(
                document_id=document.id,
                action="Share Document",
                description=description,
                created_by=current_user.id,
            )

            await uow.commit()

        logger.info(
            "Document shared successfully (document_id=%s, users=%d)",
            document_id,
            len(shared_list),
        )
        return shared_list

    async def get_shared_users(
        self,
        document_id: UUID4,
        current_user: User | None = None,
    ) -> list[ShareDocument] | Error:
        logger.info("Fetching shared users for document (document_id=%s)", document_id)

        user_id: UUID4 | None = None
        if current_user is not None:
            result = await _permission_checker(
                current_user, "documents.share", "documents.share_my"
            )
            if isinstance(result, Error):
                return result
            can_share_all = result is None or "documents.share" in result
            user_id = None if can_share_all else current_user.id

        async with self._unit_of_work as uow:
            # Verify document exists
            document = await uow.document_repository.get_document_by_id(
                document_id, user_id=user_id
            )
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            # Get shared users
            shares = await uow.document_repository.get_shared_users(document_id)

        logger.info(
            "Shared users fetched successfully (document_id=%s, count=%d)",
            document_id,
            len(shares),
        )
        return shares

    async def get_document_users(
        self,
        document_id: UUID4,
        current_user: User,
    ) -> list[User] | Error:
        logger.info("Fetching document users (document_id=%s)", document_id)

        result = await _permission_checker(current_user, "reminders.create")
        if isinstance(result, Error):
            return result

        async with self._unit_of_work as uow:
            document = await uow.document_repository.get_document_by_id(document_id)
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            shares = await uow.document_repository.get_shared_users(document_id)

            seen_ids: set = {current_user.id}  # exclude the reminder creator
            users: list[User] = []
            for user in [document.assigned_user, document.creator] + [
                s.user for s in shares
            ]:
                if user.id not in seen_ids:
                    seen_ids.add(user.id)
                    users.append(user)

        logger.info(
            "Document users fetched successfully (document_id=%s, count=%d)",
            document_id,
            len(users),
        )
        return users

    async def delete_share_document(
        self,
        document_id: UUID4,
        share_id: UUID4,
        current_user: User,
    ) -> Message | Error:
        logger.info("Deleting share document (share_id=%s)", share_id)

        result = await _permission_checker(
            current_user, "documents.delete_share", "documents.delete_share_my"
        )
        if isinstance(result, Error):
            return result
        can_delete_all = result is None or "documents.delete_share" in result
        scope_user_id = None if can_delete_all else current_user.id

        async with self._unit_of_work as uow:
            # Verify document exists
            document = await uow.document_repository.get_document_by_id(
                document_id, user_id=scope_user_id
            )
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            # Only the document creator can revoke shares
            if document.created_by != current_user.id:
                logger.warning(
                    "Share deletion rejected: user is not the creator (id=%s, user=%s, creator=%s)",
                    document_id,
                    current_user.id,
                    document.created_by,
                )
                return Error(
                    detail="Only the document creator can manage document shares",
                    code=status.HTTP_403_FORBIDDEN,
                )

            # Verify share exists and belongs to this document
            share = await uow.document_repository.get_share_by_id(share_id)
            if not share:
                logger.warning("Share not found (share_id=%s)", share_id)
                return Error(detail="Share not found", code=status.HTTP_404_NOT_FOUND)

            if share.document_id != document_id:
                logger.warning(
                    "Share does not belong to document (share_id=%s, document_id=%s)",
                    share_id,
                    document_id,
                )
                return Error(
                    detail="Share does not belong to this document",
                    code=status.HTTP_400_BAD_REQUEST,
                )

            # Delete the share
            revoked_user_id = share.user_id
            await uow.document_repository.delete_share_document(share_id)

            # Cascade: remove revoked user from all reminder assigned_users for this document
            reminders = (
                await uow.reminder_repository.get_document_reminders_assigned_to_user(
                    document_id, revoked_user_id
                )
            )
            for reminder in reminders:
                reminder.assigned_users = [
                    u for u in reminder.assigned_users if u.id != revoked_user_id
                ]
                if not reminder.assigned_users:
                    await uow.reminder_repository.delete_reminder(reminder.id)

            # Create document history entry
            user_name = f"{share.user.first_name} {share.user.last_name}"
            description = (
                f"Share document '{document.name}' deleted, removed user: {user_name}"
            )
            await uow.history_repository.create_document_history(
                document_id=document.id,
                action="Share Document Delete",
                description=description,
                created_by=current_user.id,
            )

            await uow.commit()

        logger.info("Share document deleted successfully (share_id=%s)", share_id)
        return Message(detail="Assigned document successfully removed!")

    async def _validate_file(self, file: UploadFile) -> Error | None:
        """Validate uploaded file"""
        if not file.filename:
            return Error(detail="No file provided", code=status.HTTP_400_BAD_REQUEST)

        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            return Error(
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
                code=status.HTTP_400_BAD_REQUEST,
            )

        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return Error(
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB",
                code=status.HTTP_400_BAD_REQUEST,
            )

        return None

    async def _save_file(
        self, file: UploadFile, version_id: UUID, document_name: str
    ) -> str:
        """Save uploaded file and return file path"""
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        file_ext = file.filename.split(".")[-1].lower()  # type: ignore
        version_id_str = str(version_id).replace("-", "")[:8]
        filename = f"{document_name}_{version_id_str}.{file_ext}"
        file_path = UPLOAD_DIR / filename

        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        return str(file_path)

    async def generate_share_link(
        self,
        document_id: UUID4,
        share_link_create: ShareLinkCreate,
        current_user: User,
    ) -> str | Error:
        """Generate encrypted shareable link for document"""
        logger.info("Generating share link (document_id=%s)", document_id)

        result = await _permission_checker(
            current_user, "documents.share", "documents.share_my"
        )
        if isinstance(result, Error):
            return result
        can_share_all = result is None or "documents.share" in result
        scope_user_id = None if can_share_all else current_user.id

        # Validate secret key is configured
        if not settings.SHARE_LINK_SECRET_KEY:
            logger.error("SHARE_LINK_SECRET_KEY not configured")
            return Error(
                detail="Share link generation not configured",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        async with self._unit_of_work as uow:
            # Verify document exists
            document = await uow.document_repository.get_document_by_id(
                document_id, user_id=scope_user_id
            )
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            # Only the document creator can generate share links
            if document.created_by != current_user.id:
                logger.warning(
                    "Share link generation rejected: user is not the creator (id=%s, user=%s, creator=%s)",
                    document_id,
                    current_user.id,
                    document.created_by,
                )
                return Error(
                    detail="Only the document creator can generate share links",
                    code=status.HTTP_403_FORBIDDEN,
                )

            # Validate expiration date
            if share_link_create.expiration_date is not None:
                try:
                    exp_date = datetime.strptime(
                        share_link_create.expiration_date, "%Y-%m-%d"
                    ).date()
                    today = date.today()
                    if exp_date < today:
                        return Error(
                            detail="Expiration date must be in the future",
                            code=status.HTTP_400_BAD_REQUEST,
                        )
                except ValueError:
                    return Error(
                        detail="Invalid date format", code=status.HTTP_400_BAD_REQUEST
                    )

            # Create encrypted data
            data = {
                "document_id": str(document_id),
                "exp_date": share_link_create.expiration_date,
                "password": share_link_create.password,
                "today": date.today().isoformat(),
            }

            # Encrypt the data
            try:
                fernet = Fernet(settings.SHARE_LINK_SECRET_KEY.encode())
                encrypted_data = fernet.encrypt(json.dumps(data).encode())
                token = urlsafe_b64encode(encrypted_data).decode()
            except Exception as e:
                logger.error("Failed to encrypt share link data: %s", str(e))
                return Error(
                    detail="Failed to generate share link",
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Create document history entry
            description = f"Share link generated for '{document.name}'"
            await uow.history_repository.create_document_history(
                document_id=document.id,
                action="Share Link Generate",
                description=description,
                created_by=current_user.id,
            )

            await uow.commit()

        logger.info("Share link generated successfully (document_id=%s)", document_id)
        return token

    async def validate_share_link(
        self,
        token: str,
        password: str | None = None,
    ) -> UUID4 | Error:
        """Validate and decrypt share link token"""
        logger.info("Validating share link")

        # Validate secret key is configured
        if not settings.SHARE_LINK_SECRET_KEY:
            logger.error("SHARE_LINK_SECRET_KEY not configured")
            return Error(
                detail="Share link validation not configured",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Decrypt the token
        try:
            fernet = Fernet(settings.SHARE_LINK_SECRET_KEY.encode())
            encrypted_data = urlsafe_b64decode(token.encode())
            decrypted_data = fernet.decrypt(encrypted_data)
            data = json.loads(decrypted_data.decode())
        except (InvalidToken, ValueError, KeyError) as e:
            logger.warning("Invalid share link token: %s", str(e))
            return Error(detail="Invalid share link", code=status.HTTP_400_BAD_REQUEST)

        # Validate expiration date
        if data.get("exp_date") is not None:
            try:
                exp_date = datetime.strptime(data["exp_date"], "%Y-%m-%d").date()
                if date.today() > exp_date:
                    logger.warning("Share link expired")
                    return Error(
                        detail="Share link expired", code=status.HTTP_403_FORBIDDEN
                    )
            except (ValueError, KeyError):
                return Error(
                    detail="Invalid share link", code=status.HTTP_400_BAD_REQUEST
                )

        # Validate password if required
        if data.get("password"):
            if not password or password != data["password"]:
                logger.warning("Invalid password for share link")
                return Error(
                    detail="Invalid or missing password",
                    code=status.HTTP_401_UNAUTHORIZED,
                )

        # Verify document still exists
        try:
            document_id = UUID4(data["document_id"])
        except (ValueError, KeyError):
            return Error(detail="Invalid share link", code=status.HTTP_400_BAD_REQUEST)

        async with self._unit_of_work as uow:
            document = await uow.document_repository.get_document_by_id(document_id)
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

        logger.info("Share link validated successfully (document_id=%s)", document_id)
        return document_id

    async def search_documents(
        self,
        request: DocumentSearchRequest,
        current_user: User | None = None,
    ) -> DocumentSearchResponse | Error:
        logger.info("Searching documents: %s", request.message)

        user_id: UUID4 | None = None
        if current_user is not None:
            result = await _permission_checker(
                current_user, "documents.search", "documents.search_my"
            )
            if isinstance(result, Error):
                return result
            can_search_all = result is None or "documents.search" in result
            user_id = None if can_search_all else current_user.id

        try:
            filters = await self._agent_service.extract_filters(request.message)
        except Exception:
            logger.exception("Filter extraction failed")
            return Error(
                detail="Search failed, please try again later",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        async with self._unit_of_work as uow:
            rows = await uow.document_repository.search_documents_with_filters(
                filters, user_id
            )

        try:
            message = await self._agent_service.format_results(request.message, rows)
        except Exception:
            logger.exception("Result formatting failed")
            return Error(
                detail="Search failed, please try again later",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return DocumentSearchResponse(message=message)

    async def chat_with_document_version(
        self,
        document_id: UUID4,
        version_id: UUID4,
        user_message: str,
        current_user: User | None = None,
    ) -> str | Error:
        logger.info(
            "Chat with document version (document_id=%s, version_id=%s)",
            document_id,
            version_id,
        )

        scope_user_id = None
        if current_user is not None:
            result = await _permission_checker(
                current_user, "documents.chat", "documents.chat_my"
            )
            if isinstance(result, Error):
                return result
            can_chat_all = result is None or "documents.chat" in result
            scope_user_id = None if can_chat_all else current_user.id

        async with self._unit_of_work as uow:
            document = await uow.document_repository.get_document_by_id(
                document_id, user_id=scope_user_id
            )
            if not document:
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )
            versions = await uow.document_repository.get_version_histories(document_id)
            version = next((v for v in versions if v.id == version_id), None)
            if not version:
                return Error(detail="Version not found", code=status.HTTP_404_NOT_FOUND)
            document_name = document.name

        user_id_str = str(current_user.id) if current_user else "anon"
        history = await self._chat_store_service.load_history(
            str(document_id), str(version_id), user_id_str
        )
        context = await self._rag_service.retrieve_context(
            str(version_id), user_message
        )
        try:
            reply = await self._agent_service.chat_with_document(
                context, document_name, history, user_message
            )
        except Exception:
            logger.exception(
                "Chat failed (document_id=%s, version_id=%s)", document_id, version_id
            )
            return Error(
                detail="Chat failed, please try again later",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        await self._chat_store_service.save_history(
            str(document_id), str(version_id), user_id_str, history
        )
        return reply
