from datetime import date
from typing import Any, Protocol
from uuid import UUID

from pydantic import UUID4
from sqlalchemy import and_, exists, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from configuration.models import Tag
from core.documents.schemas import DocumentCreate, DocumentUpdate
from core.models import (
    Document,
    DocumentComment,
    Reminder,
    ShareDocument,
    VersionHistory,
)


class DocumentRepository(Protocol):
    async def create_document(
        self, document_create: DocumentCreate, created_by: UUID
    ) -> Document: ...

    async def update_document(
        self, document_id: UUID4, document_update: DocumentUpdate
    ) -> Document: ...

    async def get_document_by_id(
        self, document_id: UUID4, user_id: UUID4 | None = None
    ) -> Document | None: ...

    async def get_document_by_name(self, name: str) -> Document | None: ...

    async def get_documents_paginated(
        self,
        skip: int,
        limit: int,
        category_id: UUID4 | None = None,
        stage_id: UUID4 | None = None,
        created_date: date | None = None,
        archive: bool = False,
        user_id: UUID | None = None,
        search: str | None = None,
    ) -> list[Document]: ...

    async def count_documents(
        self,
        category_id: UUID4 | None = None,
        stage_id: UUID4 | None = None,
        created_date: date | None = None,
        archive: bool = False,
        user_id: UUID | None = None,
        search: str | None = None,
    ) -> int: ...

    async def create_version_history(
        self,
        document_id: UUID,
        document_file: str,
        version_number: int,
        created_by: UUID,
    ) -> VersionHistory: ...

    async def delete_document(self, document_id: UUID4) -> None: ...

    async def get_version_histories(
        self, document_id: UUID4
    ) -> list[VersionHistory]: ...

    async def get_current_version(
        self, document_id: UUID4
    ) -> VersionHistory | None: ...

    async def delete_version_histories(self, document_id: UUID4) -> None: ...

    async def update_version_file_path(
        self, version_id: UUID, file_path: str
    ) -> VersionHistory: ...

    async def archive_document(self, document_id: UUID4, archive: bool) -> Document: ...

    async def create_comment(
        self, document_id: UUID4, user_id: UUID, comment: str
    ) -> DocumentComment: ...

    async def get_comments(self, document_id: UUID4) -> list[DocumentComment]: ...

    async def share_document(
        self,
        document_id: UUID4,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ShareDocument: ...

    async def get_shared_users(self, document_id: UUID4) -> list[ShareDocument]: ...

    async def check_existing_share(
        self, document_id: UUID4, user_id: UUID
    ) -> ShareDocument | None: ...

    async def get_share_by_id(self, share_id: UUID4) -> ShareDocument | None: ...

    async def delete_share_document(self, share_id: UUID4) -> None: ...

    async def get_documents_by_category(self) -> list[tuple[str, int]]: ...

    async def get_documents_by_subcategory(self) -> list[tuple[str, int]]: ...

    async def get_db_schema(self) -> str: ...

    async def execute_search_sql(self, sql: str) -> list[dict[str, Any]]: ...


class DocumentRepositoryImpl(DocumentRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_document(
        self, document_create: DocumentCreate, created_by: UUID
    ) -> Document:
        document = Document(
            name=document_create.name,
            category_id=document_create.category_id,
            subcategory_id=document_create.subcategory_id,
            stage_id=document_create.stage_id,
            assigned_to=document_create.assigned_to,
            description=document_create.description,
            created_by=created_by,
        )

        # Handle tags if provided
        if document_create.tag_ids:
            result = await self.session.execute(
                select(Tag).where(Tag.id.in_(document_create.tag_ids))
            )
            tags = list(result.scalars().all())
            document.tags = tags

        self.session.add(document)
        await self.session.flush()
        await self.session.refresh(document, ["tags"])
        return document

    async def get_document_by_id(
        self, document_id: UUID4, user_id: UUID4 | None = None
    ) -> Document | None:
        query = (
            select(Document)
            .where(Document.id == document_id)
            .options(
                selectinload(Document.stage),
                selectinload(Document.assigned_user),
                selectinload(Document.creator),
                selectinload(Document.category),
                selectinload(Document.subcategory),
                selectinload(Document.tags),
            )
        )
        if user_id:
            # Check if document is shared with the user (respecting date constraints)
            shared_subquery = exists().where(
                and_(
                    ShareDocument.document_id == Document.id,
                    ShareDocument.user_id == user_id,
                    or_(
                        ShareDocument.start_date.is_(None),
                        ShareDocument.start_date <= func.current_date(),
                    ),
                    or_(
                        ShareDocument.end_date.is_(None),
                        ShareDocument.end_date >= func.current_date(),
                    ),
                )
            )
            query = query.where(
                or_(
                    Document.created_by == user_id,
                    Document.assigned_to == user_id,
                    shared_subquery,
                )
            )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_document_by_name(self, name: str) -> Document | None:
        result = await self.session.execute(
            select(Document).where(Document.name == name)
        )
        return result.scalars().first()

    async def update_document(
        self, document_id: UUID4, document_update: DocumentUpdate
    ) -> Document:
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalars().first()
        if not document:
            raise ValueError(f"Document with id {document_id} not found")

        document.name = document_update.name
        document.category_id = document_update.category_id
        document.subcategory_id = document_update.subcategory_id
        document.stage_id = document_update.stage_id
        document.assigned_to = document_update.assigned_to
        document.description = document_update.description

        # Handle tags update
        if document_update.tag_ids is not None:
            result = await self.session.execute(
                select(Tag).where(Tag.id.in_(document_update.tag_ids))
            )
            tags = list(result.scalars().all())
            document.tags = tags
        else:
            document.tags = []

        await self.session.flush()
        await self.session.refresh(document, ["tags"])
        return document

    async def get_documents_paginated(
        self,
        skip: int,
        limit: int,
        category_id: UUID4 | None = None,
        stage_id: UUID4 | None = None,
        created_date: date | None = None,
        archive: bool = False,
        user_id: UUID | None = None,
        search: str | None = None,
    ) -> list[Document]:
        query = select(Document)

        # Apply filters
        if category_id:
            query = query.where(Document.category_id == category_id)
        if stage_id:
            query = query.where(Document.stage_id == stage_id)
        if created_date:
            query = query.where(func.date(Document.created_at) == created_date)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Document.name.ilike(search_pattern),
                    Document.description.ilike(search_pattern),
                )
            )
        if user_id:
            # Check if document is shared with the user (respecting date constraints)
            shared_subquery = exists().where(
                and_(
                    ShareDocument.document_id == Document.id,
                    ShareDocument.user_id == user_id,
                    or_(
                        ShareDocument.start_date.is_(None),
                        ShareDocument.start_date <= func.current_date(),
                    ),
                    or_(
                        ShareDocument.end_date.is_(None),
                        ShareDocument.end_date >= func.current_date(),
                    ),
                )
            )
            query = query.where(
                or_(
                    Document.created_by == user_id,
                    Document.assigned_to == user_id,
                    shared_subquery,
                )
            )
        query = query.where(Document.archive == archive)

        # Eagerly load relationships
        query = query.options(
            selectinload(Document.stage),
            selectinload(Document.assigned_user),
            selectinload(Document.creator),
            selectinload(Document.category),
            selectinload(Document.subcategory),
            selectinload(Document.tags),
        )

        # Order by created_at descending (most recent first)
        query = query.order_by(Document.created_at.desc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_documents(
        self,
        category_id: UUID4 | None = None,
        stage_id: UUID4 | None = None,
        created_date: date | None = None,
        archive: bool = False,
        user_id: UUID | None = None,
        search: str | None = None,
    ) -> int:
        query = select(func.count(Document.id))

        # Apply same filters
        if category_id:
            query = query.where(Document.category_id == category_id)
        if stage_id:
            query = query.where(Document.stage_id == stage_id)
        if created_date:
            query = query.where(func.date(Document.created_at) == created_date)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Document.name.ilike(search_pattern),
                    Document.description.ilike(search_pattern),
                )
            )
        if user_id:
            # Check if document is shared with the user (respecting date constraints)
            shared_subquery = exists().where(
                and_(
                    ShareDocument.document_id == Document.id,
                    ShareDocument.user_id == user_id,
                    or_(
                        ShareDocument.start_date.is_(None),
                        ShareDocument.start_date <= func.current_date(),
                    ),
                    or_(
                        ShareDocument.end_date.is_(None),
                        ShareDocument.end_date >= func.current_date(),
                    ),
                )
            )
            query = query.where(
                or_(
                    Document.created_by == user_id,
                    Document.assigned_to == user_id,
                    shared_subquery,
                )
            )
        query = query.where(Document.archive == archive)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create_version_history(
        self,
        document_id: UUID,
        document_file: str,
        version_number: int,
        created_by: UUID,
    ) -> VersionHistory:
        result = await self.session.execute(
            select(VersionHistory).where(VersionHistory.document_id == document_id)
        )
        previous_versions = result.scalars().all()
        for version in previous_versions:
            version.is_current = False

        version_history = VersionHistory(
            document_id=document_id,
            document_file=document_file,
            version_number=version_number,
            is_current=True,
            created_by=created_by,
        )
        self.session.add(version_history)
        await self.session.flush()
        await self.session.refresh(version_history, ["creator"])
        return version_history

    async def delete_document(self, document_id: UUID4) -> None:
        # First delete all reminders associated with this document
        reminders_result = await self.session.execute(
            select(Reminder).where(Reminder.document_id == document_id)
        )
        reminders = reminders_result.scalars().all()
        for reminder in reminders:
            await self.session.delete(reminder)

        # Then delete the document
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalars().first()
        if document:
            await self.session.delete(document)
            await self.session.flush()

    async def get_version_histories(self, document_id: UUID4) -> list[VersionHistory]:
        result = await self.session.execute(
            select(VersionHistory)
            .where(VersionHistory.document_id == document_id)
            .options(selectinload(VersionHistory.creator))
            .order_by(VersionHistory.version_number.desc())
        )
        return list(result.scalars().all())

    async def get_current_version(self, document_id: UUID4) -> VersionHistory | None:
        result = await self.session.execute(
            select(VersionHistory)
            .where(VersionHistory.document_id == document_id)
            .where(VersionHistory.is_current == True)  # noqa: E712
        )
        return result.scalars().first()

    async def delete_version_histories(self, document_id: UUID4) -> None:
        result = await self.session.execute(
            select(VersionHistory).where(VersionHistory.document_id == document_id)
        )
        versions = result.scalars().all()
        for version in versions:
            await self.session.delete(version)

    async def update_version_file_path(
        self, version_id: UUID, file_path: str
    ) -> VersionHistory:
        result = await self.session.execute(
            select(VersionHistory).where(VersionHistory.id == version_id)
        )
        version = result.scalars().first()
        if not version:
            raise ValueError(f"Version with id {version_id} not found")

        version.document_file = file_path
        await self.session.flush()
        await self.session.refresh(version, ["creator"])
        return version

    async def archive_document(self, document_id: UUID4, archive: bool) -> Document:
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalars().first()
        if not document:
            raise ValueError(f"Document with id {document_id} not found")

        document.archive = archive
        await self.session.flush()
        await self.session.refresh(
            document,
            [
                "stage",
                "assigned_user",
                "creator",
                "category",
                "subcategory",
                "tags",
            ],
        )
        return document

    async def create_comment(
        self, document_id: UUID4, user_id: UUID, comment: str
    ) -> DocumentComment:
        document_comment = DocumentComment(
            document_id=document_id,
            user_id=user_id,
            comment=comment,
        )
        self.session.add(document_comment)
        await self.session.flush()
        await self.session.refresh(document_comment, ["user"])
        return document_comment

    async def get_comments(self, document_id: UUID4) -> list[DocumentComment]:
        result = await self.session.execute(
            select(DocumentComment)
            .where(DocumentComment.document_id == document_id)
            .options(selectinload(DocumentComment.user))
            .order_by(DocumentComment.created_at)
        )
        return list(result.scalars().all())

    async def share_document(
        self,
        document_id: UUID4,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ShareDocument:
        share = ShareDocument(
            document_id=document_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )
        self.session.add(share)
        await self.session.flush()
        await self.session.refresh(share, ["user"])
        return share

    async def get_shared_users(self, document_id: UUID4) -> list[ShareDocument]:
        result = await self.session.execute(
            select(ShareDocument)
            .where(ShareDocument.document_id == document_id)
            .options(selectinload(ShareDocument.user))
            .order_by(ShareDocument.created_at.desc())
        )
        return list(result.scalars().all())

    async def check_existing_share(
        self, document_id: UUID4, user_id: UUID
    ) -> ShareDocument | None:
        result = await self.session.execute(
            select(ShareDocument)
            .where(ShareDocument.document_id == document_id)
            .where(ShareDocument.user_id == user_id)
        )
        return result.scalars().first()

    async def get_share_by_id(self, share_id: UUID4) -> ShareDocument | None:
        result = await self.session.execute(
            select(ShareDocument)
            .where(ShareDocument.id == share_id)
            .options(selectinload(ShareDocument.user))
        )
        return result.scalars().first()

    async def delete_share_document(self, share_id: UUID4) -> None:
        result = await self.session.execute(
            select(ShareDocument).where(ShareDocument.id == share_id)
        )
        share = result.scalars().first()
        if share:
            await self.session.delete(share)
            await self.session.flush()

    async def get_documents_by_category(self) -> list[tuple[str, int]]:
        from configuration.models import Category

        result = await self.session.execute(
            select(Category.title, func.count(Document.id))
            .join(Document, Document.category_id == Category.id)
            .group_by(Category.title)
            .order_by(func.count(Document.id).desc())
        )
        return [(row[0], row[1]) for row in result.all()]

    async def get_documents_by_subcategory(self) -> list[tuple[str, int]]:
        from configuration.models import Subcategory

        result = await self.session.execute(
            select(Subcategory.title, func.count(Document.id))
            .join(Document, Document.subcategory_id == Subcategory.id)
            .group_by(Subcategory.title)
            .order_by(func.count(Document.id).desc())
        )
        return [(row[0], row[1]) for row in result.all()]

    async def get_db_schema(self) -> str:
        _DOCUMENT_ALLOWED_TABLES = [
            "documents",
            "version_histories",
            "document_histories",
            "document_comments",
            "share_documents",
            "document_tags",
            "categories",
            "subcategories",
            "stages",
            "tags",
        ]
        result = await self.session.execute(
            text("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = ANY(:allowed_tables)
            ORDER BY table_name, ordinal_position
            """),
            {"allowed_tables": _DOCUMENT_ALLOWED_TABLES},
        )
        tables: dict[str, list[str]] = {}
        for row in result.fetchall():
            table = str(row.table_name)
            col = f"{row.column_name} ({row.data_type})"
            if table not in tables:
                tables[table] = []
            tables[table].append(col)
        lines = ["Database tables:"]
        for table, cols in sorted(tables.items()):
            lines.append(f"- {table}: {', '.join(cols)}")
        return "\n".join(lines)

    async def execute_search_sql(self, sql: str) -> list[dict[str, Any]]:
        result = await self.session.execute(text(sql))
        return [dict(row._mapping) for row in result.fetchall()]
