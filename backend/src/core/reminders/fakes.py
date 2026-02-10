from datetime import date, datetime, time
from typing import Any
from uuid import UUID, uuid4

from pydantic import UUID4
from starlette import status

from core.models import (
    Document,
    Reminder,
)
from core.reminders.repository import ReminderRepository
from core.reminders.schemas import PaginatedReminderResponse, ReminderUpdate
from core.reminders.service import ReminderService
from schemas import Error, Message


class FakeReminderRepository(ReminderRepository):
    def __init__(self, session: Any = None):
        self.session = session
        self.documents: dict[UUID, Document] = {}
        self.reminders: dict[UUID, Reminder] = {}

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

    async def get_reminders_by_document(
        self, document_id: UUID4, user_id: UUID4 | None = None
    ) -> list[Reminder]:
        reminders = [
            reminder
            for reminder in self.reminders.values()
            if reminder.document_id == document_id
        ]
        if user_id:
            reminders = [
                r
                for r in reminders
                if r.created_by == user_id
                or user_id in [a.id for a in r.assigned_users]
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

    async def delete_reminder(self, reminder_id: UUID4) -> None:
        if reminder_id in self.reminders:
            del self.reminders[reminder_id]


class FakeReminderService(ReminderService):
    def __init__(self):
        self.reminders: dict[UUID, Reminder] = {}
        self.documents: dict[UUID, Document] = {}

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

    async def create_reminder(
        self,
        document_id: UUID4,
        reminder_create,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Reminder | Error:
        from auth.models import User

        # Verify document exists
        document = self.documents.get(document_id)
        if not document or (user_id and document.created_by != user_id):
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
        for user_id_assign in reminder_create.assign_user:
            user = User(
                id=user_id_assign,
                first_name="Mock",
                last_name="User",
                username=f"mockuser-{user_id_assign}",
                password="hashed",  # nosec B106
                is_active=True,
            )
            reminder.assigned_users.append(user)

        self.reminders[reminder.id] = reminder
        return reminder

    async def get_reminders_by_document(
        self,
        document_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> list[Reminder] | Error:
        # Verify document exists
        document = self.documents.get(document_id)
        if not document or (user_id and document.created_by != user_id):
            return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

        reminders = [
            reminder
            for reminder in self.reminders.values()
            if reminder.document_id == document_id
        ]
        # Sort by created_at descending
        reminders.sort(key=lambda x: x.created_at, reverse=True)
        return reminders
