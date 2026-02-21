import logging
from datetime import datetime, time
from typing import Protocol

from dependency_injector.wiring import Provide, inject
from pydantic import UUID4
from starlette import status

from core.models import Reminder
from core.reminders.schemas import (
    PaginatedReminderResponse,
    ReminderCreate,
    ReminderUpdate,
)
from schemas import Error, Message
from unit_of_work.uow import UnitOfWork

logger = logging.getLogger(__name__)


class ReminderService(Protocol):
    async def get_all_reminders_paginated(
        self,
        page: int,
        page_size: int,
        document_id: UUID4 | None = None,
        user_id: UUID4 | None = None,
    ) -> PaginatedReminderResponse | Error: ...

    async def get_reminder_by_id(
        self,
        reminder_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Reminder | Error: ...

    async def create_reminder(
        self,
        document_id: UUID4,
        reminder_create: ReminderCreate,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Reminder | Error: ...

    async def get_reminders_by_document(
        self,
        document_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> list[Reminder] | Error: ...

    async def update_reminder(
        self,
        reminder_id: UUID4,
        reminder_update: ReminderUpdate,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Reminder | Error: ...

    async def delete_reminder(
        self, reminder_id: UUID4, current_user_id: UUID4, user_id: UUID4 | None = None
    ) -> Message | Error: ...


class ReminderServiceImpl(ReminderService):
    @inject
    def __init__(self, unit_of_work: UnitOfWork = Provide["unit_of_work"]):
        self._unit_of_work = unit_of_work

    async def get_all_reminders_paginated(
        self,
        page: int,
        page_size: int,
        document_id: UUID4 | None = None,
        user_id: UUID4 | None = None,
    ) -> PaginatedReminderResponse | Error:
        logger.info(
            "Fetching reminders (page=%s, page_size=%s, document_id=%s)",
            page,
            page_size,
            document_id,
        )

        skip = (page - 1) * page_size

        async with self._unit_of_work as uow:
            reminders = await uow.reminder_repository.get_reminders_paginated(
                skip=skip, limit=page_size, document_id=document_id, user_id=user_id
            )
            total_rows = await uow.reminder_repository.count_reminders(
                document_id=document_id, user_id=user_id
            )

        total_pages = (total_rows + page_size - 1) // page_size

        return PaginatedReminderResponse(
            data=reminders,
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    async def get_reminder_by_id(
        self,
        reminder_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Reminder | Error:
        logger.info("Fetching reminder (id=%s)", reminder_id)

        async with self._unit_of_work as uow:
            reminder = await uow.reminder_repository.get_reminder_by_id(
                reminder_id, user_id=user_id
            )
            if not reminder:
                logger.warning("Reminder not found (id=%s)", reminder_id)
                return Error(
                    detail="Reminder not found", code=status.HTTP_404_NOT_FOUND
                )

        return reminder

    async def update_reminder(
        self,
        reminder_id: UUID4,
        reminder_update: ReminderUpdate,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Reminder | Error:
        logger.info(
            "Updating reminder (id=%s, user_id=%s)", reminder_id, current_user_id
        )

        async with self._unit_of_work as uow:
            # Verify reminder exists
            reminder = await uow.reminder_repository.get_reminder_by_id(
                reminder_id, user_id=user_id
            )
            if not reminder:
                logger.warning("Reminder not found (id=%s)", reminder_id)
                return Error(
                    detail="Reminder not found", code=status.HTTP_404_NOT_FOUND
                )

            try:
                reminder_date = datetime.strptime(
                    reminder_update.date, "%Y-%m-%d"
                ).date()
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
                    detail="Invalid date or time format",
                    code=status.HTTP_400_BAD_REQUEST,
                )

            for user_id in reminder_update.assign_user:
                user = await uow.user_repository.get_user_by_id(user_id)
                if not user:
                    logger.warning(
                        "Reminder update rejected: assigned user not found (user_id=%s)",
                        user_id,
                    )
                    return Error(
                        detail=f"User not found: {user_id}",
                        code=status.HTTP_404_NOT_FOUND,
                    )

            # Update reminder
            updated_reminder = await uow.reminder_repository.update_reminder(
                reminder_id=reminder_id,
                date_val=reminder_date,
                time_val=reminder_time,
                subject=reminder_update.subject,
                message=reminder_update.message,
                assign_user_ids=reminder_update.assign_user,
            )

            # Log document history
            await uow.history_repository.create_document_history(
                document_id=reminder.document_id,
                action="Update reminder",
                description=f"Update reminder for {reminder.document.name}",
                created_by=current_user_id,
            )

            await uow.commit()

        logger.info("Reminder updated successfully (id=%s)", reminder_id)
        return updated_reminder

    async def delete_reminder(
        self,
        reminder_id: UUID4,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Message | Error:
        """Delete a reminder"""
        logger.info(
            "Deleting reminder (id=%s, user_id=%s)", reminder_id, current_user_id
        )

        async with self._unit_of_work as uow:
            # Verify reminder exists
            reminder = await uow.reminder_repository.get_reminder_by_id(
                reminder_id, user_id=user_id
            )
            if not reminder:
                logger.warning("Reminder not found (id=%s)", reminder_id)
                return Error(
                    detail="Reminder not found", code=status.HTTP_404_NOT_FOUND
                )

            # Log document history before deleting
            await uow.history_repository.create_document_history(
                document_id=reminder.document_id,
                action="Delete reminder",
                description=f"Delete reminder for {reminder.document.name}",
                created_by=current_user_id,
            )

            # Delete reminder
            await uow.reminder_repository.delete_reminder(reminder_id)
            await uow.commit()

        logger.info("Reminder deleted successfully (id=%s)", reminder_id)
        return Message(detail="Reminder deleted successfully")

    async def create_reminder(
        self,
        document_id: UUID4,
        reminder_create: ReminderCreate,
        current_user_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> Reminder | Error:
        """Create a reminder for a document"""
        logger.info(
            "Creating reminder (document_id=%s, user_id=%s)",
            document_id,
            current_user_id,
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

            try:
                reminder_date = datetime.strptime(
                    reminder_create.date, "%Y-%m-%d"
                ).date()
                # Parse time string to time object
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
                    detail="Invalid date or time format",
                    code=status.HTTP_400_BAD_REQUEST,
                )

            # Verify all assigned users exist
            for user_id in reminder_create.assign_user:
                user = await uow.user_repository.get_user_by_id(user_id)
                if not user:
                    logger.warning(
                        "Reminder creation rejected: assigned user not found (user_id=%s)",
                        user_id,
                    )
                    return Error(
                        detail=f"User not found: {user_id}",
                        code=status.HTTP_404_NOT_FOUND,
                    )

            # Create reminder
            reminder = await uow.reminder_repository.create_reminder(
                document_id=document_id,
                date_val=reminder_date,
                time_val=reminder_time,
                subject=reminder_create.subject,
                message=reminder_create.message,
                assign_user_ids=reminder_create.assign_user,
                created_by=current_user_id,
            )

            # Log document history
            await uow.history_repository.create_document_history(
                document_id=document_id,
                action="Create reminder",
                description=f"Create reminder for {document.name}",
                created_by=current_user_id,
            )

            await uow.commit()

        logger.info("Reminder created successfully (id=%s)", reminder.id)
        return reminder

    async def get_reminders_by_document(
        self,
        document_id: UUID4,
        user_id: UUID4 | None = None,
    ) -> list[Reminder] | Error:
        """Get all reminders for a document"""
        logger.info("Fetching reminders (document_id=%s)", document_id)

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

            reminders = await uow.reminder_repository.get_reminders_by_document(
                document_id, user_id=user_id
            )

        return reminders
