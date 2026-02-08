import os
import sys
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import UploadFile
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from configuration.models import Category, Stage, Subcategory
from core.documents.schemas import DocumentCreate
from core.documents.service import DocumentServiceImpl
from core.reminders.service import ReminderServiceImpl
from schemas import Error
from unit_of_work.fake_uow import FakeUnitOfWork


@pytest.fixture
def uow():
    """Provide a fake unit of work with test data."""
    uow = FakeUnitOfWork()

    # Add test category
    category_id = uuid4()
    uow.category_repository.categories[category_id] = Category(
        id=category_id, title="Test Category"
    )

    # Add test subcategory
    subcategory_id = uuid4()
    uow.subcategory_repository.subcategories[subcategory_id] = Subcategory(
        id=subcategory_id, title="Test Subcategory", category_id=category_id
    )

    # Add test stage
    stage_id = uuid4()
    uow.stage_repository.stages[stage_id] = Stage(
        id=stage_id, title="Test Stage", color="#000000"
    )

    # Add test user
    from auth.models import User

    user_id = uuid4()
    uow.user_repository.users[user_id] = User(
        id=user_id,
        first_name="Test",
        last_name="User",
        username="testuser",
        password="hashed",
        is_active=True,
    )

    uow.test_category_id = category_id
    uow.test_subcategory_id = subcategory_id
    uow.test_stage_id = stage_id
    uow.test_user_id = user_id

    return uow


@pytest.fixture
def document_service(uow):
    """Provide a document service with fake UoW."""
    return DocumentServiceImpl(unit_of_work=uow)


@pytest.fixture
def reminder_service(uow):
    """Provide a reminder service with fake UoW."""
    return ReminderServiceImpl(unit_of_work=uow)


def create_upload_file(filename: str = "test.pdf", content: bytes = b"test content"):
    """Helper to create an UploadFile for testing."""
    file = BytesIO(content)
    return UploadFile(filename=filename, file=file)


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_create_reminder_success(document_service, reminder_service, uow):
    """Test creating a reminder successfully."""
    from auth.models import User
    from configuration.models import Tag
    from core.reminders.schemas import ReminderCreate

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create users to assign reminder to
    user_id1 = uuid4()
    user_id2 = uuid4()
    uow.user_repository.users[user_id1] = User(
        id=user_id1,
        first_name="User",
        last_name="One",
        username="user1",
        password="hashed",
        is_active=True,
    )
    uow.user_repository.users[user_id2] = User(
        id=user_id2,
        first_name="User",
        last_name="Two",
        username="user2",
        password="hashed",
        is_active=True,
    )

    # Create document
    document_data = DocumentCreate(
        name="Test Document for Reminder",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Create reminder
    reminder_data = ReminderCreate(
        date="2026-12-31",
        time="14:30",
        subject="Important Meeting",
        message="Don't forget the quarterly review meeting",
        assign_user=[user_id1, user_id2],
    )

    result = await reminder_service.create_reminder(
        document_id=document_id,
        reminder_create=reminder_data,
        current_user_id=uow.test_user_id,
    )

    assert not isinstance(result, Error)
    assert result.document_id == document_id
    assert result.subject == "Important Meeting"
    assert result.message == "Don't forget the quarterly review meeting"
    assert len(result.assigned_users) == 2


@pytest.mark.asyncio
async def test_create_reminder_document_not_found(reminder_service):
    """Test creating reminder for non-existent document fails."""
    from core.reminders.schemas import ReminderCreate

    non_existent_document_id = uuid4()
    user_id = uuid4()

    reminder_data = ReminderCreate(
        date="2026-12-31",
        time="14:30",
        subject="Test Reminder",
        message="Test message",
        assign_user=[user_id],
    )

    result = await reminder_service.create_reminder(
        document_id=non_existent_document_id,
        reminder_create=reminder_data,
        current_user_id=uuid4(),
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "document not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_create_reminder_user_not_found(document_service, reminder_service, uow):
    """Test creating reminder with non-existent user fails."""
    from configuration.models import Tag
    from core.reminders.schemas import ReminderCreate

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create document
    document_data = DocumentCreate(
        name="Test Document",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert not isinstance(created_document, Error)

    # Create reminder with non-existent user
    non_existent_user_id = uuid4()
    reminder_data = ReminderCreate(
        date="2026-12-31",
        time="14:30",
        subject="Test Reminder",
        message="Test message",
        assign_user=[non_existent_user_id],
    )

    result = await reminder_service.create_reminder(
        document_id=created_document.id,
        reminder_create=reminder_data,
        current_user_id=uow.test_user_id,
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "user not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_update_reminder_success(document_service, reminder_service, uow):
    """Test updating a reminder successfully."""
    from auth.models import User
    from configuration.models import Tag
    from core.reminders.schemas import ReminderCreate, ReminderUpdate

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create users
    user_id1 = uuid4()
    user_id2 = uuid4()
    user_id3 = uuid4()
    uow.user_repository.users[user_id1] = User(
        id=user_id1,
        first_name="User",
        last_name="One",
        username="user1",
        password="hashed",
        is_active=True,
    )
    uow.user_repository.users[user_id2] = User(
        id=user_id2,
        first_name="User",
        last_name="Two",
        username="user2",
        password="hashed",
        is_active=True,
    )
    uow.user_repository.users[user_id3] = User(
        id=user_id3,
        first_name="User",
        last_name="Three",
        username="user3",
        password="hashed",
        is_active=True,
    )

    # Create document
    document_data = DocumentCreate(
        name="Test Document",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert not isinstance(created_document, Error)

    # Create reminder
    reminder_data = ReminderCreate(
        date="2026-12-31",
        time="14:30",
        subject="Original Subject",
        message="Original message",
        assign_user=[user_id1],
    )

    created_reminder = await reminder_service.create_reminder(
        document_id=created_document.id,
        reminder_create=reminder_data,
        current_user_id=uow.test_user_id,
    )

    assert not isinstance(created_reminder, Error)

    # Update reminder
    update_data = ReminderUpdate(
        date="2027-01-15",
        time="16:00",
        subject="Updated Subject",
        message="Updated message",
        assign_user=[user_id2, user_id3],
    )

    result = await reminder_service.update_reminder(
        reminder_id=created_reminder.id,
        reminder_update=update_data,
        current_user_id=uow.test_user_id,
    )

    assert not isinstance(result, Error)
    assert result.subject == "Updated Subject"
    assert result.message == "Updated message"
    assert len(result.assigned_users) == 2


@pytest.mark.asyncio
async def test_update_reminder_not_found(reminder_service):
    """Test updating non-existent reminder fails."""
    from core.reminders.schemas import ReminderUpdate

    non_existent_reminder_id = uuid4()

    update_data = ReminderUpdate(
        date="2027-01-15",
        time="16:00",
        subject="Updated Subject",
        message="Updated message",
        assign_user=[uuid4()],
    )

    result = await reminder_service.update_reminder(
        reminder_id=non_existent_reminder_id,
        reminder_update=update_data,
        current_user_id=uuid4(),
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "reminder not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_reminder_by_id_success(document_service, reminder_service, uow):
    """Test getting a reminder by ID successfully."""
    from auth.models import User
    from configuration.models import Tag
    from core.reminders.schemas import ReminderCreate

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create user
    user_id = uuid4()
    uow.user_repository.users[user_id] = User(
        id=user_id,
        first_name="Test",
        last_name="User",
        username="testuser",
        password="hashed",
        is_active=True,
    )

    # Create document
    document_data = DocumentCreate(
        name="Test Document",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert not isinstance(created_document, Error)

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
        current_user_id=uow.test_user_id,
    )

    assert not isinstance(created_reminder, Error)

    # Get reminder by ID
    result = await reminder_service.get_reminder_by_id(reminder_id=created_reminder.id)

    assert not isinstance(result, Error)
    assert result.id == created_reminder.id
    assert result.subject == "Test Reminder"


@pytest.mark.asyncio
async def test_get_reminder_by_id_not_found(reminder_service):
    """Test getting non-existent reminder fails."""
    non_existent_reminder_id = uuid4()

    result = await reminder_service.get_reminder_by_id(
        reminder_id=non_existent_reminder_id
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "reminder not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_reminders_by_document_success(
    document_service, reminder_service, uow
):
    """Test getting all reminders for a document."""
    from auth.models import User
    from configuration.models import Tag
    from core.reminders.schemas import ReminderCreate

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create user
    user_id = uuid4()
    uow.user_repository.users[user_id] = User(
        id=user_id,
        first_name="Test",
        last_name="User",
        username="testuser",
        password="hashed",
        is_active=True,
    )

    # Create document
    document_data = DocumentCreate(
        name="Test Document",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert not isinstance(created_document, Error)

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
        current_user_id=uow.test_user_id,
    )

    await reminder_service.create_reminder(
        document_id=created_document.id,
        reminder_create=reminder_data2,
        current_user_id=uow.test_user_id,
    )

    # Get all reminders for document
    result = await reminder_service.get_reminders_by_document(
        document_id=created_document.id
    )

    assert not isinstance(result, Error)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_reminders_by_document_not_found(reminder_service):
    """Test getting reminders for non-existent document fails."""
    non_existent_document_id = uuid4()

    result = await reminder_service.get_reminders_by_document(
        document_id=non_existent_document_id
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "document not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_all_reminders_paginated_success(
    reminder_service, document_service, uow
):
    """Test getting paginated reminders."""
    from auth.models import User
    from configuration.models import Tag
    from core.reminders.schemas import ReminderCreate

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create user
    user_id = uuid4()
    uow.user_repository.users[user_id] = User(
        id=user_id,
        first_name="Test",
        last_name="User",
        username="testuser",
        password="hashed",
        is_active=True,
    )

    # Create document
    document_data = DocumentCreate(
        name="Test Document",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert not isinstance(created_document, Error)

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
            current_user_id=uow.test_user_id,
        )

    # Get paginated reminders
    result = await reminder_service.get_all_reminders_paginated(page=1, page_size=3)

    assert not isinstance(result, Error)
    assert len(result.data) == 3
    assert result.current_page == 1
    assert result.total_rows == 5
    assert result.total_pages == 2
    assert result.has_next is True
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_get_all_reminders_paginated_with_document_filter(
    reminder_service, document_service, uow
):
    """Test getting paginated reminders filtered by document."""
    from auth.models import User
    from configuration.models import Tag
    from core.reminders.schemas import ReminderCreate

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create user
    user_id = uuid4()
    uow.user_repository.users[user_id] = User(
        id=user_id,
        first_name="Test",
        last_name="User",
        username="testuser",
        password="hashed",
        is_active=True,
    )

    # Create two documents
    document_data1 = DocumentCreate(
        name="Document 1",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    document_data2 = DocumentCreate(
        name="Document 2",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    upload_file1 = create_upload_file("test1.pdf")
    created_document1 = await document_service.create_document(
        document_data1, upload_file1, uow.test_user_id
    )

    upload_file2 = create_upload_file("test2.pdf")
    created_document2 = await document_service.create_document(
        document_data2, upload_file2, uow.test_user_id
    )

    assert not isinstance(created_document1, Error)
    assert not isinstance(created_document2, Error)

    # Create reminders for both documents
    for i in range(3):
        reminder_data = ReminderCreate(
            date="2026-12-31",
            time="14:30",
            subject=f"Doc1 Reminder {i + 1}",
            message=f"Message {i + 1}",
            assign_user=[user_id],
        )

        await reminder_service.create_reminder(
            document_id=created_document1.id,
            reminder_create=reminder_data,
            current_user_id=uow.test_user_id,
        )

    for i in range(2):
        reminder_data = ReminderCreate(
            date="2026-12-31",
            time="14:30",
            subject=f"Doc2 Reminder {i + 1}",
            message=f"Message {i + 1}",
            assign_user=[user_id],
        )

        await reminder_service.create_reminder(
            document_id=created_document2.id,
            reminder_create=reminder_data,
            current_user_id=uow.test_user_id,
        )

    # Get paginated reminders for document 1 only
    result = await reminder_service.get_all_reminders_paginated(
        page=1, page_size=10, document_id=created_document1.id
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 3
    assert result.total_rows == 3


@pytest.mark.asyncio
async def test_delete_reminder_success(document_service, reminder_service, uow):
    """Test deleting a reminder successfully."""
    from auth.models import User
    from configuration.models import Tag
    from core.reminders.schemas import ReminderCreate

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create user
    user_id = uuid4()
    uow.user_repository.users[user_id] = User(
        id=user_id,
        first_name="Test",
        last_name="User",
        username="testuser",
        password="hashed",
        is_active=True,
    )

    # Create document
    document_data = DocumentCreate(
        name="Test Document",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert not isinstance(created_document, Error)

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
        current_user_id=uow.test_user_id,
    )

    assert not isinstance(created_reminder, Error)

    # Delete reminder
    result = await reminder_service.delete_reminder(
        reminder_id=created_reminder.id,
        current_user_id=uow.test_user_id,
    )

    assert not isinstance(result, Error)
    assert "deleted successfully" in result.detail.lower()

    # Verify reminder is deleted
    get_result = await reminder_service.get_reminder_by_id(
        reminder_id=created_reminder.id
    )

    assert isinstance(get_result, Error)
    assert get_result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_reminder_not_found(reminder_service):
    """Test deleting non-existent reminder fails."""
    non_existent_reminder_id = uuid4()

    result = await reminder_service.delete_reminder(
        reminder_id=non_existent_reminder_id,
        current_user_id=uuid4(),
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "reminder not found" in result.detail.lower()
