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
from fastapi import UploadFile
from pydantic import UUID4
from starlette import status

from config import settings
from core.documents.agents import format_results, generate_sql, validate_sql_tables
from core.documents.schemas import (
    DocumentCommentCreate,
    DocumentCreate,
    DocumentResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentUpdate,
    PaginatedDocumentResponse,
    ShareDocumentCreate,
    ShareLinkCreate,
)
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
        page: int,
        page_size: int,
        category_id: UUID4 | None = None,
        stage_id: UUID4 | None = None,
        created_date: date | None = None,
        archive: bool = False,
        user_id: UUID4 | None = None,
        search: str | None = None,
    ) -> PaginatedDocumentResponse | Error: ...

    async def create_document(
        self,
        document_create: DocumentCreate,
        document_file: UploadFile,
        current_user_id: UUID,
    ) -> Document | Error: ...

    async def update_document(
        self,
        document_id: UUID4,
        document_update: DocumentUpdate,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Document | Error: ...

    async def delete_document(
        self, document_id: UUID4, current_user_id: UUID4, user_id: UUID4 | None = None
    ) -> Message | Error: ...

    async def get_document_by_id(
        self, document_id: UUID4, user_id: UUID4 | None = None
    ) -> Document | Error: ...

    async def get_document_file_path(
        self, document_id: UUID4, user_id: UUID4 | None = None
    ) -> str | Error: ...

    async def get_version_history(
        self, document_id: UUID4, user_id: UUID4 | None = None
    ) -> list[VersionHistory] | Error: ...

    async def create_new_version(
        self,
        document_id: UUID4,
        document_file: UploadFile,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> VersionHistory | Error: ...

    async def get_version_file_path(
        self, document_id: UUID4, version_id: UUID4, user_id: UUID4 | None = None
    ) -> str | Error: ...

    async def archive_document(
        self, document_id: UUID4, current_user_id: UUID4, user_id: UUID4 | None = None
    ) -> Document | Error: ...

    async def create_comment(
        self,
        document_id: UUID4,
        comment_create: DocumentCommentCreate,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> DocumentComment | Error: ...

    async def get_document_comments(
        self, document_id: UUID4, user_id: UUID4 | None = None
    ) -> list[DocumentComment] | Error: ...

    async def share_document(
        self,
        document_id: UUID4,
        share_data: ShareDocumentCreate,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> list[ShareDocument] | Error: ...

    async def get_shared_users(
        self,
        document_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> list[ShareDocument] | Error: ...

    async def delete_share_document(
        self,
        document_id: UUID4,
        share_id: UUID4,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Message | Error: ...

    async def generate_share_link(
        self,
        document_id: UUID4,
        share_link_create: ShareLinkCreate,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> str | Error: ...

    async def validate_share_link(
        self,
        token: str,
        password: str | None = None,
    ) -> UUID4 | Error: ...

    async def search_documents(
        self, request: DocumentSearchRequest, user_id: UUID4 | None = None
    ) -> DocumentSearchResponse | Error: ...


class DocumentServiceImpl(DocumentService):
    @inject
    def __init__(self, unit_of_work: UnitOfWork = Provide["unit_of_work"]):
        self._unit_of_work = unit_of_work

    async def get_all_documents_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        category_id: UUID4 | None = None,
        stage_id: UUID4 | None = None,
        created_date: date | None = None,
        archive: bool = False,
        user_id: UUID4 | None = None,
        search: str | None = None,
    ) -> PaginatedDocumentResponse | Error:
        logger.debug(
            "Fetching documents (page=%s, page_size=%s, category_id=%s, "
            "stage_id=%s, created_date=%s, archive=%s, search=%s)",
            page,
            page_size,
            category_id,
            stage_id,
            created_date,
            archive,
            search,
        )

        skip = (page - 1) * page_size
        limit = page_size

        async with self._unit_of_work as uow:
            documents = await uow.document_repository.get_documents_paginated(
                skip=skip,
                limit=limit,
                category_id=category_id,
                stage_id=stage_id,
                created_date=created_date,
                archive=archive,
                user_id=user_id,
                search=search,
            )
            total_rows = await uow.document_repository.count_documents(
                category_id=category_id,
                stage_id=stage_id,
                created_date=created_date,
                archive=archive,
                user_id=user_id,
                search=search,
            )

        total_pages = (total_rows + page_size - 1) // page_size

        logger.info(
            "Documents fetched (page=%s, page_size=%s, total_rows=%s, total_pages=%s)",
            page,
            page_size,
            total_rows,
            total_pages,
        )
        return PaginatedDocumentResponse(
            data=[DocumentResponse.model_validate(doc) for doc in documents],
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    async def create_document(
        self,
        document_create: DocumentCreate,
        document_file: UploadFile,
        current_user_id: UUID,
    ) -> Document | Error:
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

            created_document = await uow.document_repository.get_document_by_id(
                document.id
            )

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
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Document | Error:
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

            # Only the document creator can update the document
            if existing_document.created_by != current_user_id:
                logger.warning(
                    "Document update rejected: user is not the creator (id=%s, user=%s, creator=%s)",
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

            document = await uow.document_repository.update_document(
                document_id, document_update
            )

            description = f"Document '{document.name}' updated"
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
        self, document_id: UUID4, current_user_id: UUID4, user_id: UUID4 | None = None
    ) -> Message | Error:
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
        self, document_id: UUID4, user_id: UUID4 | None = None
    ) -> Document | Error:
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
        self, document_id: UUID4, user_id: UUID4 | None = None
    ) -> str | Error:
        logger.info("Fetching document file path (id=%s)", document_id)

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
        self, document_id: UUID4, user_id: UUID4 | None = None
    ) -> list[VersionHistory] | Error:
        logger.info("Fetching version history (document_id=%s)", document_id)

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
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> VersionHistory | Error:
        logger.info("Creating new version (document_id=%s)", document_id)

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

            await uow.commit()

        logger.info(
            "New version created successfully (document_id=%s, version=%d)",
            document_id,
            next_version_number,
        )
        return version

    async def get_version_file_path(
        self, document_id: UUID4, version_id: UUID4, user_id: UUID4 | None = None
    ) -> str | Error:
        logger.info(
            "Fetching version file path (document_id=%s, version_id=%s)",
            document_id,
            version_id,
        )

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
        self, document_id: UUID4, current_user_id: UUID4, user_id: UUID4 | None = None
    ) -> Document | Error:
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
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> DocumentComment | Error:
        logger.info("Creating comment for document (document_id=%s)", document_id)

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
                user_id=current_user_id,
                comment=comment_create.comment,
            )

            # Create document history entry
            description = f"Comment created for '{document.name}'"
            await uow.history_repository.create_document_history(
                document_id=document.id,
                action="Comment Create",
                description=description,
                created_by=current_user_id,
            )

            await uow.commit()

        logger.info("Comment created successfully (document_id=%s)", document_id)
        return comment

    async def get_document_comments(
        self, document_id: UUID4, user_id: UUID4 | None = None
    ) -> list[DocumentComment] | Error:
        logger.info("Fetching comments for document (document_id=%s)", document_id)

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
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> list[ShareDocument] | Error:
        logger.info("Sharing document (document_id=%s)", document_id)

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
                document_id, user_id=user_id
            )
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            # Only the document creator can share the document
            if document.created_by != current_user_id:
                logger.warning(
                    "Document sharing rejected: user is not the creator (id=%s, user=%s, creator=%s)",
                    document_id,
                    current_user_id,
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
            for user_id in share_data.user_ids:
                # Verify user exists
                user = await uow.user_repository.get_user_by_id(user_id)
                if not user:
                    logger.warning("User not found (user_id=%s)", user_id)
                    return Error(
                        detail=f"User not found: {user_id}",
                        code=status.HTTP_404_NOT_FOUND,
                    )

                # Check if already shared with this user
                existing_share = await uow.document_repository.check_existing_share(
                    document_id, user_id
                )
                if existing_share:
                    logger.warning(
                        "Document already shared with user (document_id=%s, user_id=%s)",
                        document_id,
                        user_id,
                    )
                    continue

                # Create share
                share = await uow.document_repository.share_document(
                    document_id=document_id,
                    user_id=user_id,
                    start_date=start_date,
                    end_date=end_date,
                )
                shared_list.append(share)

            # Create document history entry
            user_names = ", ".join([str(user_id) for user_id in share_data.user_ids])
            description = f"Document '{document.name}' shared with users: {user_names}"
            await uow.history_repository.create_document_history(
                document_id=document.id,
                action="Share Document",
                description=description,
                created_by=current_user_id,
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
        user_id: UUID4 | None = None,
    ) -> list[ShareDocument] | Error:
        logger.info("Fetching shared users for document (document_id=%s)", document_id)

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

    async def delete_share_document(
        self,
        document_id: UUID4,
        share_id: UUID4,
        current_user_id: UUID,
        user_id: UUID4 | None = None,
    ) -> Message | Error:
        logger.info("Deleting share document (share_id=%s)", share_id)

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

            # Only the document creator can manage shares
            if document.created_by != current_user_id:
                logger.warning(
                    "Share deletion rejected: user is not the creator (id=%s, user=%s, creator=%s)",
                    document_id,
                    current_user_id,
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
            await uow.document_repository.delete_share_document(share_id)

            # Create document history entry
            user_name = f"{share.user.first_name} {share.user.last_name}"
            description = (
                f"Share document '{document.name}' deleted, removed user: {user_name}"
            )
            await uow.history_repository.create_document_history(
                document_id=document.id,
                action="Share Document Delete",
                description=description,
                created_by=current_user_id,
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
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> str | Error:
        """Generate encrypted shareable link for document"""
        logger.info("Generating share link (document_id=%s)", document_id)

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
                document_id, user_id=user_id
            )
            if not document:
                logger.warning("Document not found (id=%s)", document_id)
                return Error(
                    detail="Document not found", code=status.HTTP_404_NOT_FOUND
                )

            # Only the document creator can generate share links
            if document.created_by != current_user_id:
                logger.warning(
                    "Share link generation rejected: user is not the creator (id=%s, user=%s, creator=%s)",
                    document_id,
                    current_user_id,
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
                created_by=current_user_id,
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
        user_id: UUID4 | None = None,
    ) -> DocumentSearchResponse | Error:
        logger.info("Searching documents: %s", request.message)

        async with self._unit_of_work as uow:
            db_schema = await uow.document_repository.get_db_schema()
        try:
            sql = await generate_sql(
                message=request.message,
                db_schema=db_schema,
                user_id=str(user_id) if user_id else None,
            )
        except Exception as e:
            logger.exception("Agent pipeline failed: %s", e)
            return Error(
                detail="Search failed, please try again later",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not validate_sql_tables(sql):
            logger.warning(
                "Generated SQL references disallowed tables, rejecting: %s", sql
            )
            return Error(
                detail="Search query is not related to documents",
                code=status.HTTP_400_BAD_REQUEST,
            )

        async with self._unit_of_work as uow:
            rows = await uow.document_repository.execute_search_sql(sql)

        try:
            message = await format_results(request.message, rows)
        except Exception as e:
            logger.exception("Agent pipeline failed: %s", e)
            return Error(
                detail="Search failed, please try again later",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return DocumentSearchResponse(message=message)
