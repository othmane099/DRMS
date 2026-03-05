from datetime import date, datetime, time
from typing import Protocol

from pydantic import UUID4
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth.models import User
from core.models import Document, Reminder, ShareDocument


class ReminderRepository(Protocol):
    async def create_reminder(
        self,
        document_id: UUID4,
        date_val: date,
        time_val: time,
        subject: str,
        message: str,
        assign_user_ids: list[UUID4],
        created_by: UUID4,
    ) -> Reminder: ...

    async def update_reminder(
        self,
        reminder_id: UUID4,
        date_val: date,
        time_val: time,
        subject: str,
        message: str,
        assign_user_ids: list[UUID4],
    ) -> Reminder: ...

    async def get_reminder_by_id(
        self,
        reminder_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Reminder | None: ...

    async def get_reminders_by_document(
        self, document_id: UUID4, user_id: UUID4 | None = None
    ) -> list[Reminder]: ...

    async def get_reminders_paginated(
        self,
        skip: int,
        limit: int,
        document_id: UUID4 | None = None,
        user_id: UUID4 | None = None,
    ) -> list[Reminder]: ...

    async def count_reminders(
        self,
        document_id: UUID4 | None = None,
        reminder_date: date | None = None,
        user_id: UUID4 | None = None,
    ) -> int: ...

    async def get_all_reminders(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        user_id: UUID4 | None = None,
    ) -> list[Reminder]: ...

    async def get_document_reminders_assigned_to_user(
        self, document_id: UUID4, user_id: UUID4
    ) -> list[Reminder]: ...

    async def get_due_reminders(self, now: datetime) -> list[Reminder]: ...

    async def mark_reminder_sent(self, reminder_id: UUID4, sent_at: datetime) -> None: ...

    async def delete_reminder(self, reminder_id: UUID4) -> None: ...


class ReminderRepositoryImpl(ReminderRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_reminder(
        self,
        document_id: UUID4,
        date_val: date,
        time_val: time,
        subject: str,
        message: str,
        assign_user_ids: list[UUID4],
        created_by: UUID4,
    ) -> Reminder:
        reminder = Reminder(
            document_id=document_id,
            date=date_val,
            time=time_val,
            subject=subject,
            message=message,
            created_by=created_by,
        )

        # Fetch and assign users to the reminder
        if assign_user_ids:
            result = await self.session.execute(
                select(User).where(User.id.in_(assign_user_ids))
            )
            users = list(result.scalars().all())
            reminder.assigned_users = users

        self.session.add(reminder)
        await self.session.flush()
        await self.session.refresh(
            reminder, ["created_at", "creator", "document", "assigned_users"]
        )
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
        result = await self.session.execute(
            select(Reminder).where(Reminder.id == reminder_id)
        )
        reminder = result.scalars().first()
        if not reminder:
            raise ValueError(f"Reminder with id {reminder_id} not found")

        reminder.date = date_val
        reminder.time = time_val
        reminder.subject = subject
        reminder.message = message

        # Update assigned users
        if assign_user_ids is not None:
            result = await self.session.execute(
                select(User).where(User.id.in_(assign_user_ids))
            )
            users = list(result.scalars().all())
            reminder.assigned_users = users

        await self.session.flush()
        await self.session.refresh(
            reminder, ["updated_at", "creator", "document", "assigned_users"]
        )
        return reminder

    async def get_reminder_by_id(
        self, reminder_id: UUID4, user_id: UUID4 | None = None
    ) -> Reminder | None:
        query = (
            select(Reminder)
            .where(Reminder.id == reminder_id)
            .options(
                selectinload(Reminder.creator),
                selectinload(Reminder.document),
                selectinload(Reminder.assigned_users),
            )
        )
        if user_id:
            query = query.where(
                or_(
                    Reminder.created_by == user_id,
                    Reminder.assigned_users.any(User.id == user_id),
                )
            )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_reminders_by_document(
        self, document_id: UUID4, user_id: UUID4 | None = None
    ) -> list[Reminder]:
        query = (
            select(Reminder)
            .where(Reminder.document_id == document_id)
            .options(
                selectinload(Reminder.creator),
                selectinload(Reminder.document),
                selectinload(Reminder.assigned_users),
            )
            .order_by(Reminder.created_at.desc())
        )
        if user_id:
            query = query.where(
                or_(
                    Reminder.created_by == user_id,
                    Reminder.assigned_users.any(User.id == user_id),
                )
            )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_reminders_paginated(
        self,
        skip: int,
        limit: int,
        document_id: UUID4 | None = None,
        user_id: UUID4 | None = None,
    ) -> list[Reminder]:
        query = select(Reminder).options(
            selectinload(Reminder.creator),
            selectinload(Reminder.document),
            selectinload(Reminder.assigned_users),
        )

        if document_id:
            query = query.where(Reminder.document_id == document_id)

        if user_id:
            query = query.where(
                or_(
                    Reminder.created_by == user_id,
                    Reminder.assigned_users.any(User.id == user_id),
                )
            )
            query = query.where(
                Reminder.document_id.in_(self._accessible_documents_subquery(user_id))
            )

        query = query.order_by(Reminder.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_reminders(
        self,
        document_id: UUID4 | None = None,
        reminder_date: date | None = None,
        user_id: UUID4 | None = None,
    ) -> int:
        query = select(func.count()).select_from(Reminder)

        if document_id:
            query = query.where(Reminder.document_id == document_id)
        if reminder_date:
            query = query.where(Reminder.date == reminder_date)
        if user_id:
            query = query.where(
                or_(
                    Reminder.created_by == user_id,
                    Reminder.assigned_users.any(User.id == user_id),
                )
            )
            query = query.where(
                Reminder.document_id.in_(self._accessible_documents_subquery(user_id))
            )

        result = await self.session.execute(query)
        return result.scalar() or 0

    def _accessible_documents_subquery(self, user_id: UUID4):
        return (
            select(Document.id)
            .outerjoin(ShareDocument, ShareDocument.document_id == Document.id)
            .where(
                or_(
                    Document.created_by == user_id,
                    Document.assigned_to == user_id,
                    ShareDocument.user_id == user_id,
                )
            )
            .distinct()
        )

    async def get_all_reminders(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        user_id: UUID4 | None = None,
    ) -> list[Reminder]:
        query = select(Reminder)
        if start_date:
            query = query.where(Reminder.date >= start_date)
        if end_date:
            query = query.where(Reminder.date <= end_date)
        if user_id:
            query = query.where(
                or_(
                    Reminder.created_by == user_id,
                    Reminder.assigned_users.any(User.id == user_id),
                )
            )
        query = query.order_by(Reminder.date, Reminder.time)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_document_reminders_assigned_to_user(
        self, document_id: UUID4, user_id: UUID4
    ) -> list[Reminder]:
        query = (
            select(Reminder)
            .where(
                Reminder.document_id == document_id,
                Reminder.assigned_users.any(User.id == user_id),
            )
            .options(selectinload(Reminder.assigned_users))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_due_reminders(self, now: datetime) -> list[Reminder]:
        """Return unsent reminders whose scheduled datetime <= now.

        PostgreSQL supports date + time → timestamp natively.
        We compare against a naive datetime to avoid tz-casting issues.
        """
        naive_now = now.replace(tzinfo=None)
        query = (
            select(Reminder)
            .where(
                Reminder.sent_at.is_(None),
                (Reminder.date + Reminder.time) <= naive_now,
            )
            .options(
                selectinload(Reminder.assigned_users),
                selectinload(Reminder.document),
                selectinload(Reminder.creator),
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_reminder_sent(self, reminder_id: UUID4, sent_at: datetime) -> None:
        await self.session.execute(
            update(Reminder)
            .where(Reminder.id == reminder_id)
            .values(sent_at=sent_at)
        )
        await self.session.flush()

    async def delete_reminder(self, reminder_id: UUID4) -> None:
        result = await self.session.execute(
            select(Reminder).where(Reminder.id == reminder_id)
        )
        reminder = result.scalars().first()
        if reminder:
            await self.session.delete(reminder)
            await self.session.flush()
