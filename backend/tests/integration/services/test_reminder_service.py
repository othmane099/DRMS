import os
import sys
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import UploadFile
from sqlalchemy import select

sys.path.insert(0, f"{os.getcwd()}/src")

from configuration.models import Category, Stage, Subcategory  # noqa: E402
from core.documents.schemas import DocumentCreate  # noqa: E402
from core.documents.service import DocumentServiceImpl
from core.reminders.service import ReminderServiceImpl  # noqa: E402
from db import default_session_factory  # noqa: E402
from schemas import Error  # noqa: E402
from unit_of_work.uow import UnitOfWorkImpl  # noqa: E402


def create_upload_file(filename: str = "test.pdf", content: bytes = b"test content"):
    """Helper to create an UploadFile for testing."""
    file = BytesIO(content)
    return UploadFile(filename=filename, file=file)


@pytest.fixture
async def test_data():
    """Create test data (category, subcategory, stage, user)."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    async with default_session_factory() as session:
        # Create category
        category = Category(title="Integration Test Category")
        session.add(category)
        await session.flush()

        # Create subcategory
        subcategory = Subcategory(
            title="Integration Test Subcategory", category_id=category.id
        )
        session.add(subcategory)
        await session.flush()

        # Create stage
        stage = Stage(title="Integration Test Stage", color="#FF0000")
        session.add(stage)
        await session.flush()

        # Create user
        user = User(
            first_name="Test",
            last_name="User",
            username="testuser_doc_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.flush()

        await session.commit()

        return {
            "category_id": category.id,
            "subcategory_id": subcategory.id,
            "stage_id": stage.id,
            "user_id": user.id,
        }


@pytest.mark.asyncio
async def test_create_reminder_integration_success(test_data):
    """Integration test: Create a reminder with real database."""
    from core.models import Reminder
    from core.reminders.schemas import ReminderCreate

    # Create shared UnitOfWork to avoid connection warnings
    uow = UnitOfWorkImpl(session_factory=default_session_factory)

    document_service = DocumentServiceImpl(unit_of_work=uow)

    reminder_service = ReminderServiceImpl(unit_of_work=uow)

    # Create document
    document_data = DocumentCreate(
        name=f"Reminder Test Doc {uuid4()}",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)

    # Create users to assign reminder to
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    user1_id = uuid4()
    user2_id = uuid4()

    async with default_session_factory() as session:
        user1 = User(
            id=user1_id,
            first_name="Reminder",
            last_name="User1",
            username=f"reminderuser1_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        user2 = User(
            id=user2_id,
            first_name="Reminder",
            last_name="User2",
            username=f"reminderuser2_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user1)
        session.add(user2)
        await session.commit()

    # Create reminder
    reminder_data = ReminderCreate(
        date="2026-12-31",
        time="14:30:00",
        subject="Important Meeting",
        message="Don't forget the quarterly review meeting",
        assign_user=[user1_id, user2_id],
    )

    result = await reminder_service.create_reminder(
        document_id=created_document.id,
        reminder_create=reminder_data,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(result, Error)
    assert result.document_id == created_document.id
    assert result.subject == "Important Meeting"
    assert result.message == "Don't forget the quarterly review meeting"
    assert len(result.assigned_users) == 2

    # Verify in database
    async with default_session_factory() as session:
        db_reminder = await session.execute(
            select(Reminder).where(Reminder.id == result.id)
        )
        reminder = db_reminder.scalar_one_or_none()
        assert reminder is not None
        assert reminder.subject == "Important Meeting"
        assert str(reminder.time) == "14:30:00"

    # Cleanup reminder, document, and users
    await reminder_service.delete_reminder(
        reminder_id=result.id, current_user_id=test_data["user_id"]
    )
    await document_service.delete_document(
        document_id=created_document.id, current_user_id=test_data["user_id"]
    )

    async with default_session_factory() as session:
        await session.execute(select(User).where(User.id == user1_id))
        user1 = (
            await session.execute(select(User).where(User.id == user1_id))
        ).scalar_one_or_none()
        if user1:
            await session.delete(user1)
        user2 = (
            await session.execute(select(User).where(User.id == user2_id))
        ).scalar_one_or_none()
        if user2:
            await session.delete(user2)
        await session.commit()


@pytest.mark.asyncio
async def test_update_reminder_integration_success(test_data):
    """Integration test: Update a reminder with real database."""
    from core.models import Reminder
    from core.reminders.schemas import ReminderCreate, ReminderUpdate

    # Create shared UnitOfWork to avoid connection warnings
    uow = UnitOfWorkImpl(session_factory=default_session_factory)

    document_service = DocumentServiceImpl(unit_of_work=uow)

    reminder_service = ReminderServiceImpl(unit_of_work=uow)

    # Create document
    document_data = DocumentCreate(
        name=f"Reminder Update Test Doc {uuid4()}",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)

    # Create users
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    user1_id = uuid4()
    user2_id = uuid4()

    async with default_session_factory() as session:
        user1 = User(
            id=user1_id,
            first_name="Reminder",
            last_name="User1",
            username=f"reminderuser1_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        user2 = User(
            id=user2_id,
            first_name="Reminder",
            last_name="User2",
            username=f"reminderuser2_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user1)
        session.add(user2)
        await session.commit()

    # Create reminder
    reminder_data = ReminderCreate(
        date="2026-12-31",
        time="14:30",
        subject="Original Subject",
        message="Original message",
        assign_user=[user1_id],
    )

    created_reminder = await reminder_service.create_reminder(
        document_id=created_document.id,
        reminder_create=reminder_data,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(created_reminder, Error)

    # Update reminder
    update_data = ReminderUpdate(
        date="2027-01-15",
        time="16:00:00",
        subject="Updated Subject",
        message="Updated message",
        assign_user=[user2_id],
    )

    result = await reminder_service.update_reminder(
        reminder_id=created_reminder.id,
        reminder_update=update_data,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(result, Error)
    assert result.subject == "Updated Subject"
    assert result.message == "Updated message"
    assert len(result.assigned_users) == 1
    assert result.assigned_users[0].id == user2_id

    # Verify in database
    async with default_session_factory() as session:
        db_reminder = await session.execute(
            select(Reminder).where(Reminder.id == result.id)
        )
        reminder = db_reminder.scalar_one_or_none()
        assert reminder is not None
        assert reminder.subject == "Updated Subject"
        assert str(reminder.time) == "16:00:00"

    # Cleanup reminder, document, and users
    await reminder_service.delete_reminder(
        reminder_id=result.id, current_user_id=test_data["user_id"]
    )
    await document_service.delete_document(
        document_id=created_document.id, current_user_id=test_data["user_id"]
    )

    async with default_session_factory() as session:
        user1 = (
            await session.execute(select(User).where(User.id == user1_id))
        ).scalar_one_or_none()
        if user1:
            await session.delete(user1)
        user2 = (
            await session.execute(select(User).where(User.id == user2_id))
        ).scalar_one_or_none()
        if user2:
            await session.delete(user2)
        await session.commit()


@pytest.mark.asyncio
async def test_get_reminder_by_id_integration_success(test_data):
    """Integration test: Get a reminder by ID with real database."""
    from core.reminders.schemas import ReminderCreate

    # Create shared UnitOfWork to avoid connection warnings
    uow = UnitOfWorkImpl(session_factory=default_session_factory)

    document_service = DocumentServiceImpl(unit_of_work=uow)

    reminder_service = ReminderServiceImpl(unit_of_work=uow)

    # Create document
    document_data = DocumentCreate(
        name=f"Reminder Get Test Doc {uuid4()}",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)

    # Create user
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    user_id = uuid4()

    async with default_session_factory() as session:
        user = User(
            id=user_id,
            first_name="Reminder",
            last_name="User",
            username=f"reminderuser_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

    # Create reminder
    reminder_data = ReminderCreate(
        date="2026-12-31",
        time="14:30",
        subject="Test Reminder",
        message="Test message",
        assign_user=[user_id],
    )

    created_reminder = await reminder_service.create_reminder(
        document_id=created_document.id,
        reminder_create=reminder_data,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(created_reminder, Error)

    # Get reminder by ID
    result = await reminder_service.get_reminder_by_id(reminder_id=created_reminder.id)

    assert not isinstance(result, Error)
    assert result.id == created_reminder.id
    assert result.subject == "Test Reminder"
    assert result.document_id == created_document.id

    # Cleanup reminder, document, and user
    await reminder_service.delete_reminder(
        reminder_id=created_reminder.id, current_user_id=test_data["user_id"]
    )
    await document_service.delete_document(
        document_id=created_document.id, current_user_id=test_data["user_id"]
    )

    async with default_session_factory() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if user:
            await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_get_reminders_by_document_integration_success(test_data):
    """Integration test: Get all reminders for a document with real database."""
    from core.reminders.schemas import ReminderCreate

    # Create shared UnitOfWork to avoid connection warnings
    uow = UnitOfWorkImpl(session_factory=default_session_factory)

    document_service = DocumentServiceImpl(unit_of_work=uow)

    reminder_service = ReminderServiceImpl(unit_of_work=uow)

    # Create document
    document_data = DocumentCreate(
        name=f"Reminder List Test Doc {uuid4()}",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)

    # Create user
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    user_id = uuid4()

    async with default_session_factory() as session:
        user = User(
            id=user_id,
            first_name="Reminder",
            last_name="User",
            username=f"reminderuser_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

    # Create multiple reminders
    reminder_data1 = ReminderCreate(
        date="2026-12-31",
        time="14:30",
        subject="First Reminder",
        message="First message",
        assign_user=[user_id],
    )

    reminder_data2 = ReminderCreate(
        date="2027-01-15",
        time="10:00",
        subject="Second Reminder",
        message="Second message",
        assign_user=[user_id],
    )

    await reminder_service.create_reminder(
        document_id=created_document.id,
        reminder_create=reminder_data1,
        current_user_id=test_data["user_id"],
    )

    await reminder_service.create_reminder(
        document_id=created_document.id,
        reminder_create=reminder_data2,
        current_user_id=test_data["user_id"],
    )

    # Get all reminders for document
    result = await reminder_service.get_reminders_by_document(
        document_id=created_document.id
    )

    assert not isinstance(result, Error)
    assert len(result) == 2

    # Cleanup document (will cascade delete reminders) and user
    await document_service.delete_document(
        document_id=created_document.id, current_user_id=test_data["user_id"]
    )

    async with default_session_factory() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if user:
            await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_get_all_reminders_paginated_integration_success(test_data):
    """Integration test: Get paginated reminders with real database."""
    from core.reminders.schemas import ReminderCreate

    # Create shared UnitOfWork to avoid connection warnings
    uow = UnitOfWorkImpl(session_factory=default_session_factory)

    document_service = DocumentServiceImpl(unit_of_work=uow)

    reminder_service = ReminderServiceImpl(unit_of_work=uow)

    # Create document
    document_data = DocumentCreate(
        name=f"Reminder Pagination Test Doc {uuid4()}",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)

    # Create user
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    user_id = uuid4()

    async with default_session_factory() as session:
        user = User(
            id=user_id,
            first_name="Reminder",
            last_name="User",
            username=f"reminderuser_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

    # Create multiple reminders
    for i in range(5):
        reminder_data = ReminderCreate(
            date="2026-12-31",
            time="14:30",
            subject=f"Reminder {i + 1}",
            message=f"Message {i + 1}",
            assign_user=[user_id],
        )

        await reminder_service.create_reminder(
            document_id=created_document.id,
            reminder_create=reminder_data,
            current_user_id=test_data["user_id"],
        )

    # Get paginated reminders
    result = await reminder_service.get_all_reminders_paginated(
        page=1, page_size=3, document_id=created_document.id
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 3
    assert result.current_page == 1
    assert result.total_rows == 5
    assert result.total_pages == 2
    assert result.has_next is True
    assert result.has_previous is False

    # Cleanup document (will cascade delete reminders) and user
    await document_service.delete_document(
        document_id=created_document.id, current_user_id=test_data["user_id"]
    )

    async with default_session_factory() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if user:
            await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_delete_reminder_integration_success(test_data):
    """Integration test: Delete a reminder with real database."""
    from core.models import Reminder
    from core.reminders.schemas import ReminderCreate

    # Create shared UnitOfWork to avoid connection warnings
    uow = UnitOfWorkImpl(session_factory=default_session_factory)

    document_service = DocumentServiceImpl(unit_of_work=uow)

    reminder_service = ReminderServiceImpl(unit_of_work=uow)

    # Create document
    document_data = DocumentCreate(
        name=f"Reminder Delete Test Doc {uuid4()}",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)

    # Create user
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    user_id = uuid4()

    async with default_session_factory() as session:
        user = User(
            id=user_id,
            first_name="Reminder",
            last_name="User",
            username=f"reminderuser_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

    # Create reminder
    reminder_data = ReminderCreate(
        date="2026-12-31",
        time="14:30",
        subject="Test Reminder",
        message="Test message",
        assign_user=[user_id],
    )

    created_reminder = await reminder_service.create_reminder(
        document_id=created_document.id,
        reminder_create=reminder_data,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(created_reminder, Error)
    reminder_id = created_reminder.id

    # Delete reminder
    result = await reminder_service.delete_reminder(
        reminder_id=reminder_id,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(result, Error)
    assert "deleted successfully" in result.detail.lower()

    # Verify deletion in database
    async with default_session_factory() as session:
        db_reminder = await session.execute(
            select(Reminder).where(Reminder.id == reminder_id)
        )
        reminder = db_reminder.scalar_one_or_none()
        assert reminder is None

    # Cleanup document and user
    await document_service.delete_document(
        document_id=created_document.id, current_user_id=test_data["user_id"]
    )

    async with default_session_factory() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if user:
            await session.delete(user)
        await session.commit()
