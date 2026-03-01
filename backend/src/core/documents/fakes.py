from datetime import date, datetime, time
from typing import Any
from uuid import UUID, uuid4

from fastapi import UploadFile
from pydantic import UUID4
from starlette import status

from core.documents.repository import DocumentRepository
from core.documents.schemas import (
    DocumentCommentCreate,
    DocumentCreate,
    DocumentFilterParams,
    DocumentResponse,
    DocumentUpdate,
    PaginatedDocumentResponse,
    ShareDocumentCreate,
    ShareLinkCreate,
)
from core.documents.service import DocumentService
from core.models import (
    Document,
    DocumentComment,
    Reminder,
    ShareDocument,
    VersionHistory,
)
from core.reminders.schemas import (
    PaginatedReminderResponse,
    ReminderCreate,
    ReminderUpdate,
)
from schemas import Error, Message


class FakeDocumentRepository(DocumentRepository):
    def __init__(self, session: Any = None):
        self.session = session
        self.documents: dict[UUID, Document] = {}
        self.version_histories: dict[UUID, VersionHistory] = {}
        self.comments: dict[UUID, DocumentComment] = {}
        self.shares: dict[UUID, ShareDocument] = {}
        self.reminders: dict[UUID, Reminder] = {}

    async def create_document(
        self, document_create: DocumentCreate, created_by: UUID
    ) -> Document:
        from auth.models import User
        from configuration.models import Category, Stage, Subcategory, Tag

        document = Document(
            id=uuid4(),
            name=document_create.name,
            category_id=document_create.category_id,
            subcategory_id=document_create.subcategory_id,
            stage_id=document_create.stage_id,
            assigned_to=document_create.assigned_to,
            description=document_create.description,
            archive=False,
            created_by=created_by,
            created_at=datetime.now(),
        )
        # Populate relationships with mock objects for validation
        document.category = Category(
            id=document_create.category_id, title="Mock Category"
        )
        document.subcategory = Subcategory(
            id=document_create.subcategory_id,
            title="Mock Subcategory",
            category_id=document_create.category_id,
        )
        document.stage = Stage(
            id=document_create.stage_id, title="Mock Stage", color="#000000"
        )
        document.creator = User(
            id=created_by,
            first_name="Mock",
            last_name="Creator",
            username="mockcreator",
            password="hashed",  # nosec B106  # nosec B106
            is_active=True,
        )
        document.assigned_user = User(
            id=document_create.assigned_to,
            first_name="Mock",
            last_name="Assigned",
            username="mockassigned",
            password="hashed",  # nosec B106  # nosec B106
            is_active=True,
        )
        # Handle tags - create mock Tag objects for the provided tag_ids
        document.tags = []
        if document_create.tag_ids:
            for tag_id in document_create.tag_ids:
                tag = Tag(id=tag_id, title=f"tag-{tag_id}")
                document.tags.append(tag)
        self.documents[document.id] = document
        return document

    async def get_document_by_id(
        self, document_id: UUID4, user_id: UUID4 | None = None
    ) -> Document | None:
        document = self.documents.get(document_id)
        if not document:
            return None

        if user_id:
            # Check if user is creator, assigned, or document is shared with them
            is_creator = document.created_by == user_id
            is_assigned = document.assigned_to == user_id
            is_shared = self._is_document_shared_with_user(document_id, user_id)

            if not (is_creator or is_assigned or is_shared):
                return None

        return document

    def _is_document_shared_with_user(self, document_id: UUID4, user_id: UUID) -> bool:
        """Check if document is shared with user (respecting date constraints)."""
        from datetime import date

        today = date.today()
        for share in self.shares.values():
            if share.document_id == document_id and share.user_id == user_id:
                # Check start_date constraint
                if share.start_date and share.start_date > today:
                    continue
                # Check end_date constraint
                if share.end_date and share.end_date < today:
                    continue
                return True
        return False

    async def get_document_by_name(self, name: str) -> Document | None:
        for doc in self.documents.values():
            if doc.name == name:
                return doc
        return None

    async def update_document(
        self, document_id: UUID4, document_update: DocumentUpdate
    ) -> Document:
        from auth.models import User
        from configuration.models import Category, Stage, Subcategory, Tag

        document = self.documents.get(document_id)
        if not document:
            raise ValueError(f"Document with id {document_id} not found")

        document.name = document_update.name
        document.category_id = document_update.category_id
        document.subcategory_id = document_update.subcategory_id
        document.stage_id = document_update.stage_id
        document.assigned_to = document_update.assigned_to
        document.description = document_update.description
        document.updated_at = datetime.now()

        # Update relationships with mock objects for validation
        document.category = Category(
            id=document_update.category_id, title="Mock Category"
        )
        document.subcategory = Subcategory(
            id=document_update.subcategory_id,
            title="Mock Subcategory",
            category_id=document_update.category_id,
        )
        document.stage = Stage(
            id=document_update.stage_id, title="Mock Stage", color="#000000"
        )
        document.assigned_user = User(
            id=document_update.assigned_to,
            first_name="Mock",
            last_name="Assigned",
            username="mockassigned",
            password="hashed",  # nosec B106
            is_active=True,
        )

        # Handle tags - create mock Tag objects for the provided tag_ids
        document.tags = []
        if document_update.tag_ids:
            for tag_id in document_update.tag_ids:
                tag = Tag(id=tag_id, title=f"tag-{tag_id}")
                document.tags.append(tag)

        return document

    async def get_documents_paginated(
        self,
        skip: int,
        limit: int,
        category_id: UUID4 | None = None,
        stage_id: UUID4 | None = None,
        created_date: date | None = None,
        archive: bool = False,
        user_id: UUID4 | None = None,
        search: str | None = None,
    ) -> list[Document]:
        docs = list(self.documents.values())

        # Apply filters
        if category_id:
            docs = [d for d in docs if d.category_id == category_id]
        if stage_id:
            docs = [d for d in docs if d.stage_id == stage_id]
        if created_date:
            docs = [
                d for d in docs if d.created_at and d.created_at.date() == created_date
            ]
        if search:
            search_lower = search.lower()
            docs = [
                d
                for d in docs
                if (d.name and search_lower in d.name.lower())
                or (d.description and search_lower in d.description.lower())
            ]
        if user_id:
            # Include documents where user is creator, assigned, or has shared access
            docs = [
                d
                for d in docs
                if d.assigned_to == user_id
                or d.created_by == user_id
                or self._is_document_shared_with_user(d.id, user_id)
            ]
        docs = [d for d in docs if d.archive == archive]

        # Sort by created_at descending
        docs = sorted(docs, key=lambda x: x.created_at or date.min, reverse=True)

        # Apply pagination
        return docs[skip : skip + limit]

    async def count_documents(
        self,
        category_id: UUID4 | None = None,
        stage_id: UUID4 | None = None,
        created_date: date | None = None,
        archive: bool = False,
        user_id: UUID4 | None = None,
        search: str | None = None,
    ) -> int:
        docs = list(self.documents.values())

        # Apply same filters
        if category_id:
            docs = [d for d in docs if d.category_id == category_id]
        if stage_id:
            docs = [d for d in docs if d.stage_id == stage_id]
        if created_date:
            docs = [
                d for d in docs if d.created_at and d.created_at.date() == created_date
            ]
        if search:
            search_lower = search.lower()
            docs = [
                d
                for d in docs
                if (d.name and search_lower in d.name.lower())
                or (d.description and search_lower in d.description.lower())
            ]
        if user_id:
            # Include documents where user is creator, assigned, or has shared access
            docs = [
                d
                for d in docs
                if d.assigned_to == user_id
                or d.created_by == user_id
                or self._is_document_shared_with_user(d.id, user_id)
            ]
        docs = [d for d in docs if d.archive == archive]

        return len(docs)

    async def create_version_history(
        self,
        document_id: UUID,
        document_file: str,
        version_number: int,
        created_by: UUID,
    ) -> VersionHistory:
        # Mark all previous versions as not current
        for version in self.version_histories.values():
            if version.document_id == document_id:
                version.is_current = False

        # Create new version
        version_history = VersionHistory(
            id=uuid4(),
            document_id=document_id,
            document_file=document_file,
            version_number=version_number,
            is_current=True,
            created_by=created_by,
            created_at=datetime.now(),
        )
        self.version_histories[version_history.id] = version_history
        return version_history

    async def delete_document(self, document_id: UUID4) -> None:
        if document_id in self.documents:
            del self.documents[document_id]

    async def get_version_histories(self, document_id: UUID4) -> list[VersionHistory]:
        return [
            v for v in self.version_histories.values() if v.document_id == document_id
        ]

    async def get_current_version(self, document_id: UUID4) -> VersionHistory | None:
        for version in self.version_histories.values():
            if version.document_id == document_id and version.is_current:
                return version
        return None

    async def delete_version_histories(self, document_id: UUID4) -> None:
        to_delete = [
            k for k, v in self.version_histories.items() if v.document_id == document_id
        ]
        for k in to_delete:
            del self.version_histories[k]

    async def update_version_file_path(
        self, version_id: UUID, file_path: str
    ) -> VersionHistory:
        version = self.version_histories.get(version_id)
        if not version:
            raise ValueError(f"Version with id {version_id} not found")

        version.document_file = file_path
        return version

    async def archive_document(
        self, document_id: UUID4, archive: bool, user_id: UUID4 | None = None
    ) -> Document:
        document = self.documents.get(document_id)
        if not document or (
            user_id
            and (document.created_by != user_id or document.assigned_to != user_id)
        ):
            raise ValueError(f"Document with id {document_id} not found")

        document.archive = archive
        document.updated_at = datetime.now()
        return document

    async def create_comment(
        self, document_id: UUID4, user_id: UUID, comment: str
    ) -> DocumentComment:
        from auth.models import User

        document_comment = DocumentComment(
            id=uuid4(),
            document_id=document_id,
            user_id=user_id,
            comment=comment,
            created_at=datetime.now(),
        )
        # Populate relationship with mock User
        document_comment.user = User(
            id=user_id,
            first_name="Mock",
            last_name="User",
            username="mockuser",
            password="hashed",  # nosec B106
            is_active=True,
        )
        self.comments[document_comment.id] = document_comment
        return document_comment

    async def get_comments(self, document_id: UUID4) -> list[DocumentComment]:
        # Get comments for the document and sort by created_at ascending
        comments = [
            comment
            for comment in self.comments.values()
            if comment.document_id == document_id
        ]
        # Sort by created_at ascending (oldest first, newest last)
        comments.sort(key=lambda x: x.created_at)
        return comments

    async def share_document(
        self,
        document_id: UUID4,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ShareDocument:
        from auth.models import User

        share = ShareDocument(
            id=uuid4(),
            document_id=document_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            created_at=datetime.now(),
        )
        # Populate relationship with mock User
        share.user = User(
            id=user_id,
            first_name="Mock",
            last_name="User",
            username="mockuser",
            password="hashed",  # nosec B106
            is_active=True,
        )
        self.shares[share.id] = share
        return share

    async def get_shared_users(self, document_id: UUID4) -> list[ShareDocument]:
        # Get shares for the document and sort by created_at descending
        shares = [
            share for share in self.shares.values() if share.document_id == document_id
        ]
        # Sort by created_at descending (most recent first)
        shares.sort(key=lambda x: x.created_at, reverse=True)
        return shares

    async def check_existing_share(
        self, document_id: UUID4, user_id: UUID
    ) -> ShareDocument | None:
        for share in self.shares.values():
            if share.document_id == document_id and share.user_id == user_id:
                return share
        return None

    async def get_share_by_id(self, share_id: UUID4) -> ShareDocument | None:
        return self.shares.get(share_id)

    async def delete_share_document(self, share_id: UUID4) -> None:
        if share_id in self.shares:
            del self.shares[share_id]

    async def create_reminder(
        self,
        document_id: UUID4,
        date_val: date,
        time_val: time,
        subject: str,
        message: str,
        assign_user_ids: list[UUID4],
        created_by: UUID,
    ) -> Reminder:
        from auth.models import User

        reminder = Reminder(
            id=uuid4(),
            document_id=document_id,
            date=date_val,
            time=time_val,
            subject=subject,
            message=message,
            created_by=created_by,
            created_at=datetime.now(),
        )

        # Populate relationships with mock objects
        reminder.creator = User(
            id=created_by,
            first_name="Mock",
            last_name="Creator",
            username="mockcreator",
            password="hashed",  # nosec B106
            is_active=True,
        )
        reminder.document = self.documents.get(document_id)  # type: ignore

        # Create mock users for assigned_users
        reminder.assigned_users = []
        for user_id in assign_user_ids:
            user = User(
                id=user_id,
                first_name="Mock",
                last_name="User",
                username=f"mockuser-{user_id}",
                password="hashed",  # nosec B106
                is_active=True,
            )
            reminder.assigned_users.append(user)

        self.reminders[reminder.id] = reminder
        return reminder

    async def update_reminder(
        self,
        reminder_id: UUID4,
        date_val: date,
        time_val: time,
        subject: str,
        message: str,
        assign_user_ids: list[UUID4],
    ) -> Reminder:
        from auth.models import User

        reminder = self.reminders.get(reminder_id)
        if not reminder:
            raise ValueError(f"Reminder with id {reminder_id} not found")

        reminder.date = date_val
        reminder.time = time_val
        reminder.subject = subject
        reminder.message = message
        reminder.updated_at = datetime.now()

        # Update assigned users
        reminder.assigned_users = []
        for user_id in assign_user_ids:
            user = User(
                id=user_id,
                first_name="Mock",
                last_name="User",
                username=f"mockuser-{user_id}",
                password="hashed",  # nosec B106
                is_active=True,
            )
            reminder.assigned_users.append(user)

        return reminder

    async def get_reminder_by_id(
        self, reminder_id: UUID4, user_id: UUID4 | None = None
    ) -> Reminder | None:
        reminder = self.reminders.get(reminder_id)
        if not reminder or (user_id and reminder.created_by != user_id):
            return None
        return reminder

    async def get_reminders_by_document(self, document_id: UUID4) -> list[Reminder]:
        reminders = [
            reminder
            for reminder in self.reminders.values()
            if reminder.document_id == document_id
        ]
        # Sort by created_at descending
        reminders.sort(key=lambda x: x.created_at, reverse=True)
        return reminders

    async def get_reminders_paginated(
        self,
        skip: int,
        limit: int,
        document_id: UUID4 | None = None,
        user_id: UUID4 | None = None,
    ) -> list[Reminder]:
        reminders = list(self.reminders.values())

        if document_id:
            reminders = [r for r in reminders if r.document_id == document_id]
        if user_id:
            reminders = [
                r
                for r in reminders
                if r.created_by == user_id
                or user_id in [a.id for a in r.assigned_users]
            ]

        # Sort by created_at descending
        reminders.sort(key=lambda x: x.created_at, reverse=True)

        # Apply pagination
        return reminders[skip : skip + limit]

    async def count_reminders(
        self,
        document_id: UUID4 | None = None,
        reminder_date: date | None = None,
        user_id: UUID4 | None = None,
    ) -> int:
        reminders = list(self.reminders.values())

        if document_id:
            reminders = [r for r in reminders if r.document_id == document_id]
        if reminder_date:
            reminders = [r for r in reminders if r.date == reminder_date]
        if user_id:
            reminders = [
                r
                for r in reminders
                if r.created_by == user_id
                or user_id in [a.id for a in r.assigned_users]
            ]

        return len(reminders)

    async def get_all_reminders(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        user_id: UUID4 | None = None,
    ) -> list[Reminder]:
        reminders = list(self.reminders.values())
        if start_date:
            reminders = [r for r in reminders if r.date >= start_date]
        if end_date:
            reminders = [r for r in reminders if r.date <= end_date]
        if user_id:
            reminders = [
                r
                for r in reminders
                if r.created_by == user_id
                or user_id in [a.id for a in r.assigned_users]
            ]
        reminders.sort(key=lambda r: (r.date, r.time))
        return reminders

    async def get_documents_by_category(self) -> list[tuple[str, int]]:
        from collections import Counter

        counts: Counter[str] = Counter()
        for doc in self.documents.values():
            if doc.category:
                counts[doc.category.title] += 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)

    async def get_documents_by_subcategory(self) -> list[tuple[str, int]]:
        from collections import Counter

        counts: Counter[str] = Counter()
        for doc in self.documents.values():
            if doc.subcategory:
                counts[doc.subcategory.title] += 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)

    async def delete_reminder(self, reminder_id: UUID4) -> None:
        if reminder_id in self.reminders:
            del self.reminders[reminder_id]


class FakeDocumentService(DocumentService):
    def __init__(self):
        self.documents: dict[UUID, Document] = {}
        self.comments: dict[UUID, DocumentComment] = {}
        self.shares: dict[UUID, ShareDocument] = {}
        self.share_links: dict[str, dict[str, Any]] = {}  # token -> data mapping
        self.reminders: dict[UUID, Reminder] = {}

    def _is_document_shared_with_user(self, document_id: UUID4, user_id: UUID) -> bool:
        """Check if document is shared with user (respecting date constraints)."""
        from datetime import date

        today = date.today()
        for share in self.shares.values():
            if share.document_id == document_id and share.user_id == user_id:
                # Check start_date constraint
                if share.start_date and share.start_date > today:
                    continue
                # Check end_date constraint
                if share.end_date and share.end_date < today:
                    continue
                return True
        return False

    async def get_all_documents_paginated(
        self,
        filters: DocumentFilterParams,
        current_user: Any,
    ) -> PaginatedDocumentResponse | Error:
        user_id = UUID4(str(current_user.id)) if filters.only_my else None

        docs = list(self.documents.values())

        # Apply filters
        if filters.category_id:
            docs = [d for d in docs if d.category_id == filters.category_id]
        if filters.stage_id:
            docs = [d for d in docs if d.stage_id == filters.stage_id]
        if filters.created_date:
            docs = [
                d
                for d in docs
                if d.created_at and d.created_at.date() == filters.created_date
            ]
        if filters.search:
            search_lower = filters.search.lower()
            docs = [
                d
                for d in docs
                if (d.name and search_lower in d.name.lower())
                or (d.description and search_lower in d.description.lower())
            ]
        if user_id:
            # Include documents where user is creator, assigned, or has shared access
            docs = [
                d
                for d in docs
                if d.assigned_to == user_id
                or d.created_by == user_id
                or self._is_document_shared_with_user(d.id, user_id)
            ]

        docs = [d for d in docs if d.archive == filters.archive]

        # Sort by created_at descending
        docs = sorted(docs, key=lambda x: x.created_at or date.min, reverse=True)

        # Pagination
        skip = (filters.page - 1) * filters.page_size
        paginated_docs = docs[skip : skip + filters.page_size]
        total_rows = len(docs)
        total_pages = (total_rows + filters.page_size - 1) // filters.page_size

        return PaginatedDocumentResponse(
            data=[DocumentResponse.model_validate(doc) for doc in paginated_docs],
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
        current_user,
        background_tasks=None,
    ) -> Document | Error:
        from auth.models import User
        from configuration.models import Category, Stage, Subcategory, Tag

        current_user_id = current_user.id

        # Check if document name already exists
        for doc in self.documents.values():
            if doc.name == document_create.name:
                return Error(
                    detail="Document name already exists",
                    code=status.HTTP_400_BAD_REQUEST,
                )

        # Create document
        document = Document(
            id=uuid4(),
            name=document_create.name,
            category_id=document_create.category_id,
            subcategory_id=document_create.subcategory_id,
            stage_id=document_create.stage_id,
            assigned_to=document_create.assigned_to,
            description=document_create.description,
            archive=False,
            created_by=current_user_id,
            created_at=datetime.now(),
        )
        # Populate relationships with mock objects for validation
        document.category = Category(
            id=document_create.category_id, title="Mock Category"
        )
        document.subcategory = Subcategory(
            id=document_create.subcategory_id,
            title="Mock Subcategory",
            category_id=document_create.category_id,
        )
        document.stage = Stage(
            id=document_create.stage_id, title="Mock Stage", color="#000000"
        )
        document.creator = User(
            id=current_user_id,
            first_name="Mock",
            last_name="User",
            username="mockuser",
            password="hashed",  # nosec B106
            is_active=True,
        )
        document.assigned_user = User(
            id=document_create.assigned_to,
            first_name="Mock",
            last_name="Assigned",
            username="mockassigned",
            password="hashed",  # nosec B106
            is_active=True,
        )
        # Handle tags - create mock Tag objects for the provided tag_ids
        document.tags = []
        if document_create.tag_ids:
            for tag_id in document_create.tag_ids:
                tag = Tag(id=tag_id, title=f"tag-{tag_id}")
                document.tags.append(tag)
        self.documents[document.id] = document
        return document

    async def update_document(
        self,
        document_id: UUID4,
        document_update: DocumentUpdate,
        current_user,
    ) -> Document | Error:
        from auth.models import User
        from configuration.models import Category, Stage, Subcategory, Tag

        current_user_id = current_user.id

        # Check if document exists and user has access
        document = self.documents.get(document_id)
        if not document:
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

        # Only the document creator can update the document
        if document.created_by != current_user_id:
            return Error(
                detail="Only the document creator can update the document",
                code=status.HTTP_403_FORBIDDEN,
            )

        # Check if name is being changed and if so, check for duplicate
        if document.name != document_update.name:
            for doc in self.documents.values():
                if doc.name == document_update.name:
                    return Error(
                        detail="Document name already exists",
                        code=status.HTTP_400_BAD_REQUEST,
                    )

        # Update document
        document.name = document_update.name
        document.category_id = document_update.category_id
        document.subcategory_id = document_update.subcategory_id
        document.stage_id = document_update.stage_id
        document.assigned_to = document_update.assigned_to
        document.description = document_update.description
        document.updated_at = datetime.now()

        # Update relationships with mock objects for validation
        document.category = Category(
            id=document_update.category_id, title="Mock Category"
        )
        document.subcategory = Subcategory(
            id=document_update.subcategory_id,
            title="Mock Subcategory",
            category_id=document_update.category_id,
        )
        document.stage = Stage(
            id=document_update.stage_id, title="Mock Stage", color="#000000"
        )
        document.assigned_user = User(
            id=document_update.assigned_to,
            first_name="Mock",
            last_name="Assigned",
            username="mockassigned",
            password="hashed",  # nosec B106
            is_active=True,
        )

        # Handle tags - create mock Tag objects for the provided tag_ids
        document.tags = []
        if document_update.tag_ids:
            for tag_id in document_update.tag_ids:
                tag = Tag(id=tag_id, title=f"tag-{tag_id}")
                document.tags.append(tag)

        return document

    async def delete_document(
        self, document_id: UUID4, current_user
    ) -> Message | Error:
        current_user_id = current_user.id
        document = self.documents.get(document_id)
        if not document:
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

        # Only the document creator can delete the document
        if document.created_by != current_user_id:
            return Error(
                detail="Only the document creator can delete the document",
                code=status.HTTP_403_FORBIDDEN,
            )

        # Delete the document
        del self.documents[document_id]
        return Message(detail="Document deleted successfully")

    async def get_document_by_id(
        self, document_id: UUID4, current_user
    ) -> Document | Error:
        document = self.documents.get(document_id)
        if not document:
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)
        return document

    async def get_document_file_path(
        self,
        document_id: UUID4,
        current_user=None,
        full_permission: str = "documents.download",
        my_permission: str = "documents.download_my",
    ) -> str | Error:
        document = self.documents.get(document_id)
        if not document:
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)
        return f"uploads/documents/{document_id}.pdf"

    async def get_version_history(
        self, document_id: UUID4, current_user=None
    ) -> list[VersionHistory] | Error:
        document = self.documents.get(document_id)
        if not document:
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)
        return []

    async def create_new_version(
        self,
        document_id: UUID4,
        document_file: UploadFile,
        current_user=None,
        background_tasks=None,
    ) -> VersionHistory | Error:
        current_user_id = current_user.id if current_user else None
        document = self.documents.get(document_id)
        if not document:
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

        # Only the document creator can create new versions
        if document.created_by != current_user_id:
            return Error(
                detail="Only the document creator can create new versions",
                code=status.HTTP_403_FORBIDDEN,
            )

        # Create a new version
        version = VersionHistory(
            id=uuid4(),
            document_id=document_id,
            document_file=f"uploads/documents/{document_id}_v2.pdf",
            version_number=2,
            is_current=True,
            created_by=current_user_id,
            created_at=datetime.now(),
        )
        return version

    async def get_version_file_path(
        self,
        document_id: UUID4,
        version_id: UUID4,
        current_user=None,
    ) -> str | Error:
        user_id = current_user.id if current_user else None
        document = self.documents.get(document_id)
        if not document or (
            user_id
            and (document.created_by != user_id or document.assigned_to != user_id)
        ):
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)
        return f"uploads/documents/{document_id}_v{version_id}.pdf"

    async def archive_document(
        self, document_id: UUID4, current_user
    ) -> Document | Error:
        current_user_id = current_user.id
        document = self.documents.get(document_id)
        if not document:
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

        # Only the document creator can archive the document
        if document.created_by != current_user_id:
            return Error(
                detail="Only the document creator can archive the document",
                code=status.HTTP_403_FORBIDDEN,
            )

        document.archive = not document.archive
        document.updated_at = datetime.now()
        return document

    async def create_comment(
        self,
        document_id: UUID4,
        comment_create: DocumentCommentCreate,
        current_user,
    ) -> DocumentComment | Error:
        from auth.models import User

        # Check if document exists
        document = self.documents.get(document_id)
        if not document:
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

        # Create comment
        comment = DocumentComment(
            id=uuid4(),
            document_id=document_id,
            user_id=current_user.id,
            comment=comment_create.comment,
            created_at=datetime.now(),
        )
        # Populate relationship with mock User
        comment.user = User(
            id=current_user.id,
            first_name="Mock",
            last_name="User",
            username="mockuser",
            password="hashed",  # nosec B106
            is_active=True,
        )
        self.comments[comment.id] = comment
        return comment

    async def get_document_comments(
        self, document_id: UUID4, current_user=None
    ) -> list[DocumentComment] | Error:
        user_id = current_user.id if current_user else None
        # Check if document exists
        document = self.documents.get(document_id)
        if not document or (
            user_id
            and (document.created_by != user_id or document.assigned_to != user_id)
        ):
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

        # Get comments for the document and sort by created_at ascending
        comments = [
            comment
            for comment in self.comments.values()
            if comment.document_id == document_id
        ]
        # Sort by created_at ascending (oldest first, newest last)
        comments.sort(key=lambda x: x.created_at)
        return comments

    async def share_document(
        self,
        document_id: UUID4,
        share_data: ShareDocumentCreate,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> list[ShareDocument] | Error:
        from auth.models import User

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

        # Check if document exists
        document = self.documents.get(document_id)
        if not document or (
            user_id
            and (document.created_by != user_id or document.assigned_to != user_id)
        ):
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

        # Only the document creator can share the document
        if document.created_by != current_user_id:
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
            # Check if already shared with this user
            existing_share = None
            for share in self.shares.values():
                if share.document_id == document_id and share.user_id == user_id:
                    existing_share = share
                    break

            if existing_share:
                continue

            # Create share
            share = ShareDocument(
                id=uuid4(),
                document_id=document_id,
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                created_at=datetime.now(),
            )
            # Populate relationship with mock User
            share.user = User(
                id=user_id,
                first_name="Mock",
                last_name="User",
                username="mockuser",
                password="hashed",  # nosec B106
                is_active=True,
            )
            self.shares[share.id] = share
            shared_list.append(share)

        return shared_list

    async def get_shared_users(
        self,
        document_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> list[ShareDocument] | Error:
        document = self.documents.get(document_id)
        if not document or (
            user_id
            and (document.created_by != user_id or document.assigned_to != user_id)
        ):
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

        # Get shares for the document and sort by created_at descending
        shares = [
            share for share in self.shares.values() if share.document_id == document_id
        ]
        # Sort by created_at descending (most recent first)
        shares.sort(key=lambda x: x.created_at, reverse=True)
        return shares

    async def delete_share_document(
        self,
        document_id: UUID4,
        share_id: UUID4,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Message | Error:
        # Check if document exists
        document = self.documents.get(document_id)
        if not document or (
            user_id
            and (document.created_by != user_id or document.assigned_to != user_id)
        ):
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

        # Only the document creator can manage shares
        if document.created_by != current_user_id:
            return Error(
                detail="Only the document creator can manage document shares",
                code=status.HTTP_403_FORBIDDEN,
            )

        # Check if share exists
        share = self.shares.get(share_id)
        if not share:
            return Error(detail="Share not found", code=status.HTTP_404_NOT_FOUND)

        # Check if share belongs to this document
        if share.document_id != document_id:
            return Error(
                detail="Share does not belong to this document",
                code=status.HTTP_400_BAD_REQUEST,
            )

        # Delete the share
        del self.shares[share_id]
        return Message(detail="Assigned document successfully removed!")

    async def generate_share_link(
        self,
        document_id: UUID4,
        share_link_create: ShareLinkCreate,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> str | Error:
        # Check if document exists
        document = self.documents.get(document_id)
        if not document or (
            user_id
            and (document.created_by != user_id or document.assigned_to != user_id)
        ):
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

        # Only the document creator can generate share links
        if document.created_by != current_user_id:
            return Error(
                detail="Only the document creator can generate share links",
                code=status.HTTP_403_FORBIDDEN,
            )

        # Validate expiration date
        if share_link_create.expiration_date is not None:
            try:
                from datetime import datetime

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

        # Generate a simple token (in real implementation this would be encrypted)
        import base64
        import json

        data = {
            "document_id": str(document_id),
            "exp_date": share_link_create.expiration_date,
            "password": share_link_create.password,
            "today": date.today().isoformat(),
        }

        # Create a fake token
        token = base64.b64encode(json.dumps(data).encode()).decode()

        # Store the link data
        self.share_links[token] = data

        return token

    async def validate_share_link(
        self,
        token: str,
        password: str | None = None,
    ) -> UUID4 | Error:
        # Retrieve the link data
        data = self.share_links.get(token)
        if not data:
            return Error(detail="Invalid share link", code=status.HTTP_400_BAD_REQUEST)

        # Validate expiration date
        try:
            from datetime import datetime

            exp_date = datetime.strptime(data["exp_date"], "%Y-%m-%d").date()
            if date.today() > exp_date:
                return Error(
                    detail="Share link expired", code=status.HTTP_403_FORBIDDEN
                )
        except (ValueError, KeyError):
            return Error(detail="Invalid share link", code=status.HTTP_400_BAD_REQUEST)

        # Validate password if required
        if data.get("password"):
            if not password or password != data["password"]:
                return Error(
                    detail="Invalid or missing password",
                    code=status.HTTP_401_UNAUTHORIZED,
                )

        # Verify document still exists
        try:
            document_id = UUID4(data["document_id"])
        except (ValueError, KeyError):
            return Error(detail="Invalid share link", code=status.HTTP_400_BAD_REQUEST)

        document = self.documents.get(document_id)
        if not document:
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

        return document_id

    async def create_reminder(
        self,
        document_id: UUID4,
        reminder_create: ReminderCreate,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Reminder | Error:
        from auth.models import User

        # Verify document exists
        document = self.documents.get(document_id)
        if not document or (
            user_id
            and (document.created_by != user_id or document.assigned_to != user_id)
        ):
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

        # Parse time string to time object
        try:
            if ":" in reminder_create.time:
                time_parts = reminder_create.time.split(":")
                if len(time_parts) == 2:
                    reminder_time = time(
                        hour=int(time_parts[0]), minute=int(time_parts[1])
                    )
                elif len(time_parts) == 3:
                    reminder_time = time(
                        hour=int(time_parts[0]),
                        minute=int(time_parts[1]),
                        second=int(time_parts[2]),
                    )
                else:
                    raise ValueError("Invalid time format")
            else:
                raise ValueError("Invalid time format")
        except (ValueError, IndexError):
            return Error(
                detail="Invalid time format",
                code=status.HTTP_400_BAD_REQUEST,
            )

        # Parse date
        try:
            reminder_date = datetime.strptime(reminder_create.date, "%Y-%m-%d").date()
        except ValueError:
            return Error(
                detail="Invalid date format",
                code=status.HTTP_400_BAD_REQUEST,
            )

        # Create reminder
        reminder = Reminder(
            id=uuid4(),
            document_id=document_id,
            date=reminder_date,
            time=reminder_time,
            subject=reminder_create.subject,
            message=reminder_create.message,
            created_by=current_user_id,
            created_at=datetime.now(),
        )

        # Populate relationships
        reminder.creator = User(
            id=current_user_id,
            first_name="Mock",
            last_name="Creator",
            username="mockcreator",
            password="hashed",  # nosec B106
            is_active=True,
        )
        reminder.document = document

        # Create mock users for assigned_users
        reminder.assigned_users = []
        for user_id in reminder_create.assign_user:
            user = User(
                id=user_id,
                first_name="Mock",
                last_name="User",
                username=f"mockuser-{user_id}",
                password="hashed",  # nosec B106
                is_active=True,
            )
            reminder.assigned_users.append(user)

        self.reminders[reminder.id] = reminder
        return reminder

    async def update_reminder(
        self,
        reminder_id: UUID4,
        reminder_update: ReminderUpdate,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Reminder | Error:
        from auth.models import User

        # Verify reminder exists
        reminder = self.reminders.get(reminder_id)
        if not reminder or (user_id and reminder.created_by != user_id):
            return Error(detail="Reminder not found", code=status.HTTP_404_NOT_FOUND)

        # Parse time string to time object
        try:
            if ":" in reminder_update.time:
                time_parts = reminder_update.time.split(":")
                if len(time_parts) == 2:
                    reminder_time = time(
                        hour=int(time_parts[0]), minute=int(time_parts[1])
                    )
                elif len(time_parts) == 3:
                    reminder_time = time(
                        hour=int(time_parts[0]),
                        minute=int(time_parts[1]),
                        second=int(time_parts[2]),
                    )
                else:
                    raise ValueError("Invalid time format")
            else:
                raise ValueError("Invalid time format")
        except (ValueError, IndexError):
            return Error(
                detail="Invalid time format",
                code=status.HTTP_400_BAD_REQUEST,
            )

        # Parse date
        try:
            reminder_date = datetime.strptime(reminder_update.date, "%Y-%m-%d").date()
        except ValueError:
            return Error(
                detail="Invalid date format",
                code=status.HTTP_400_BAD_REQUEST,
            )

        # Update reminder
        reminder.date = reminder_date
        reminder.time = reminder_time
        reminder.subject = reminder_update.subject
        reminder.message = reminder_update.message
        reminder.updated_at = datetime.now()

        # Update assigned users
        reminder.assigned_users = []
        for user_id in reminder_update.assign_user:
            user = User(
                id=user_id,
                first_name="Mock",
                last_name="User",
                username=f"mockuser-{user_id}",
                password="hashed",  # nosec B106
                is_active=True,
            )
            reminder.assigned_users.append(user)

        return reminder

    async def get_reminder_by_id(
        self,
        reminder_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Reminder | Error:
        reminder = self.reminders.get(reminder_id)
        if not reminder or (user_id and reminder.created_by != user_id):
            return Error(detail="Reminder not found", code=status.HTTP_404_NOT_FOUND)
        return reminder

    async def get_reminders_by_document(
        self,
        document_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> list[Reminder] | Error:
        document = self.documents.get(document_id)
        if not document or (
            user_id
            and (document.created_by != user_id or document.assigned_to != user_id)
        ):
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

        reminders = [
            reminder
            for reminder in self.reminders.values()
            if reminder.document_id == document_id
        ]
        # Sort by created_at descending
        reminders.sort(key=lambda x: x.created_at, reverse=True)
        return reminders

    async def get_all_reminders_paginated(
        self,
        page: int,
        page_size: int,
        document_id: UUID4 | None = None,
        user_id: UUID4 | None = None,
    ) -> PaginatedReminderResponse | Error:
        reminders = list(self.reminders.values())

        if document_id:
            reminders = [r for r in reminders if r.document_id == document_id]

        if user_id:
            reminders = [
                r
                for r in reminders
                if r.created_by == user_id
                or user_id in [a.id for a in r.assigned_users]
            ]

        # Sort by created_at descending
        reminders.sort(key=lambda x: x.created_at, reverse=True)

        # Pagination
        skip = (page - 1) * page_size
        paginated_reminders = reminders[skip : skip + page_size]
        total_rows = len(reminders)
        total_pages = (total_rows + page_size - 1) // page_size

        return PaginatedReminderResponse(
            data=paginated_reminders,
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    async def delete_reminder(
        self, reminder_id: UUID4, current_user_id: UUID4, user_id: UUID4 | None = None
    ) -> Message | Error:
        # Verify reminder exists
        reminder = self.reminders.get(reminder_id)
        if not reminder or (user_id and reminder.created_by != user_id):
            return Error(detail="Reminder not found", code=status.HTTP_404_NOT_FOUND)

        # Delete reminder
        del self.reminders[reminder_id]
        return Message(detail="Reminder deleted successfully")
