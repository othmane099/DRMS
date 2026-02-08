import os
import sys
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette import status

sys.path.append(f"{os.getcwd()}/src")


@pytest.fixture
def reminder_service(document_service):
    """Provide a fake reminder service with access to documents."""
    from core.reminders.fakes import FakeReminderService

    service = FakeReminderService()
    # Share documents dictionary reference so reminders can access them
    service.documents = document_service.documents
    return service


@pytest.fixture
def document_service():
    """Provide a fake document service with test data."""
    from auth.models import User
    from configuration.models import Category, Stage, Subcategory
    from core.documents.fakes import FakeDocumentService

    service = FakeDocumentService()

    category_id = uuid4()
    subcategory_id = uuid4()
    stage_id = uuid4()
    user_id = uuid4()

    category = Category(id=category_id, title="Test Category")
    subcategory = Subcategory(
        id=subcategory_id, title="Test Subcategory", category_id=category_id
    )
    stage = Stage(id=stage_id, title="Test Stage", color="#000000")
    user = User(
        id=user_id,
        first_name="Test",
        last_name="User",
        username="testuser",
        password="hashed",
        is_active=True,
    )

    # Create test documents
    from datetime import datetime

    from core.models import Document

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        name="Test Document",
        category_id=category_id,
        subcategory_id=subcategory_id,
        stage_id=stage_id,
        assigned_to=user_id,
        archive=False,
        created_by=user_id,
        created_at=datetime.now(),
    )
    doc.category = category
    doc.subcategory = subcategory
    doc.stage = stage
    doc.creator = user
    doc.assigned_user = user
    doc.tags = []
    service.documents[doc_id] = doc

    return service


@pytest.mark.asyncio
async def test_create_reminder_success(document_service, reminder_service):
    """Test POST /documents/{document_id}/reminders endpoint success."""
    from auth.models import User
    from core.documents.api import create_reminder
    from core.reminders.schemas import ReminderCreate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Create users to assign
    user_id1 = uuid4()
    user_id2 = uuid4()

    # Create reminder
    reminder_data = ReminderCreate(
        date="2026-12-31",
        time="14:30",
        subject="Important Meeting",
        message="Don't forget the quarterly review",
        assign_user=[user_id1, user_id2],
    )

    result = await create_reminder(
        document_id=doc_id,
        reminder_create=reminder_data,
        current_user=User(
            id=uuid4(),
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        ),
        reminder_service=reminder_service,
    )

    assert result.document_id == doc_id
    assert result.subject == "Important Meeting"
    assert result.message == "Don't forget the quarterly review"
    assert len(result.assigned_users) == 2


@pytest.mark.asyncio
async def test_create_reminder_document_not_found(reminder_service):
    """Test POST /documents/{document_id}/reminders endpoint with non-existent document."""
    from auth.models import User
    from core.documents.api import create_reminder
    from core.reminders.schemas import ReminderCreate

    non_existent_doc_id = uuid4()

    reminder_data = ReminderCreate(
        date="2026-12-31",
        time="14:30",
        subject="Test",
        message="Test message",
        assign_user=[uuid4()],
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_reminder(
            document_id=non_existent_doc_id,
            reminder_create=reminder_data,
            current_user=User(
                id=uuid4(),
                first_name="Test",
                last_name="User",
                username="testuser",
                password="hashed",
                is_active=True,
            ),
            reminder_service=reminder_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_update_reminder_success(document_service, reminder_service):
    """Test PUT /reminders/{reminder_id} endpoint success."""
    from auth.models import User
    from core.documents.api import create_reminder
    from core.reminders.api import update_reminder
    from core.reminders.schemas import ReminderCreate, ReminderUpdate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Create reminder first
    user_id1 = uuid4()
    reminder_data = ReminderCreate(
        date="2026-12-31",
        time="14:30",
        subject="Original Subject",
        message="Original message",
        assign_user=[user_id1],
    )

    created = await create_reminder(
        document_id=doc_id,
        reminder_create=reminder_data,
        current_user=User(
            id=uuid4(),
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        ),
        reminder_service=reminder_service,
    )

    # Update reminder
    user_id2 = uuid4()
    update_data = ReminderUpdate(
        date="2027-01-15",
        time="16:00",
        subject="Updated Subject",
        message="Updated message",
        assign_user=[user_id2],
    )

    result = await update_reminder(
        reminder_id=created.id,
        reminder_update=update_data,
        current_user=User(
            id=uuid4(),
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        ),
        reminder_service=reminder_service,
    )

    assert result.subject == "Updated Subject"
    assert result.message == "Updated message"


@pytest.mark.asyncio
async def test_update_reminder_not_found(reminder_service):
    """Test PUT /reminders/{reminder_id} endpoint with non-existent reminder."""
    from auth.models import User
    from core.reminders.api import update_reminder
    from core.reminders.schemas import ReminderUpdate

    non_existent_reminder_id = uuid4()

    update_data = ReminderUpdate(
        date="2027-01-15",
        time="16:00",
        subject="Updated Subject",
        message="Updated message",
        assign_user=[uuid4()],
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_reminder(
            reminder_id=non_existent_reminder_id,
            reminder_update=update_data,
            current_user=User(
                id=uuid4(),
                first_name="Test",
                last_name="User",
                username="testuser",
                password="hashed",
                is_active=True,
            ),
            reminder_service=reminder_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_reminder_success(document_service, reminder_service):
    """Test GET /reminders/{reminder_id} endpoint success."""
    from auth.models import User
    from core.documents.api import create_reminder
    from core.reminders.api import get_reminder
    from core.reminders.schemas import ReminderCreate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Create reminder first
    reminder_data = ReminderCreate(
        date="2026-12-31",
        time="14:30",
        subject="Test Reminder",
        message="Test message",
        assign_user=[uuid4()],
    )

    created = await create_reminder(
        document_id=doc_id,
        reminder_create=reminder_data,
        current_user=User(
            id=uuid4(),
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        ),
        reminder_service=reminder_service,
    )

    # Get reminder
    result = await get_reminder(
        reminder_id=created.id,
        reminder_service=reminder_service,
    )

    assert result.id == created.id
    assert result.subject == "Test Reminder"


@pytest.mark.asyncio
async def test_get_reminder_not_found(reminder_service):
    """Test GET /reminders/{reminder_id} endpoint with non-existent reminder."""
    from core.reminders.api import get_reminder

    non_existent_reminder_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await get_reminder(
            reminder_id=non_existent_reminder_id,
            reminder_service=reminder_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_document_reminders_success(document_service, reminder_service):
    """Test GET /documents/{document_id}/reminders endpoint success."""
    from auth.models import User
    from core.documents.api import create_reminder, get_document_reminders
    from core.reminders.schemas import ReminderCreate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Create multiple reminders
    for i in range(3):
        reminder_data = ReminderCreate(
            date="2026-12-31",
            time="14:30",
            subject=f"Reminder {i + 1}",
            message=f"Message {i + 1}",
            assign_user=[uuid4()],
        )

        await create_reminder(
            document_id=doc_id,
            reminder_create=reminder_data,
            current_user=User(
                id=uuid4(),
                first_name="Test",
                last_name="User",
                username="testuser",
                password="hashed",
                is_active=True,
            ),
            reminder_service=reminder_service,
        )

    # Get all reminders for document
    result = await get_document_reminders(
        document_id=doc_id,
        reminder_service=reminder_service,
    )

    assert len(result) == 3


@pytest.mark.asyncio
async def test_get_document_reminders_not_found(reminder_service):
    """Test GET /documents/{document_id}/reminders endpoint with non-existent document."""
    from core.documents.api import get_document_reminders

    non_existent_doc_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await get_document_reminders(
            document_id=non_existent_doc_id,
            reminder_service=reminder_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_all_reminders_paginated_success(document_service, reminder_service):
    """Test GET /reminders endpoint with pagination."""
    from auth.models import User
    from core.documents.api import create_reminder
    from core.reminders.api import get_all_reminders
    from core.reminders.schemas import ReminderCreate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Create multiple reminders
    for i in range(5):
        reminder_data = ReminderCreate(
            date="2026-12-31",
            time="14:30",
            subject=f"Reminder {i + 1}",
            message=f"Message {i + 1}",
            assign_user=[uuid4()],
        )

        await create_reminder(
            document_id=doc_id,
            reminder_create=reminder_data,
            current_user=User(
                id=uuid4(),
                first_name="Test",
                last_name="User",
                username="testuser",
                password="hashed",
                is_active=True,
            ),
            reminder_service=reminder_service,
        )

    # Get paginated reminders
    result = await get_all_reminders(
        page=1,
        page_size=3,
        document_id=None,
        reminder_service=reminder_service,
    )

    assert len(result.data) == 3
    assert result.current_page == 1
    assert result.total_rows == 5
    assert result.total_pages == 2
    assert result.has_next is True
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_get_all_reminders_with_document_filter(
    document_service, reminder_service
):
    """Test GET /reminders endpoint with document filter."""
    from auth.models import User
    from core.documents.api import create_reminder
    from core.reminders.api import get_all_reminders
    from core.reminders.schemas import ReminderCreate

    # Get documents
    doc_ids = list(document_service.documents.keys())
    doc_id1 = doc_ids[0]
    doc_id2 = doc_ids[1] if len(doc_ids) > 1 else doc_id1

    # Create reminders for doc1
    for i in range(3):
        reminder_data = ReminderCreate(
            date="2026-12-31",
            time="14:30",
            subject=f"Doc1 Reminder {i + 1}",
            message=f"Message {i + 1}",
            assign_user=[uuid4()],
        )

        await create_reminder(
            document_id=doc_id1,
            reminder_create=reminder_data,
            current_user=User(
                id=uuid4(),
                first_name="Test",
                last_name="User",
                username="testuser",
                password="hashed",
                is_active=True,
            ),
            reminder_service=reminder_service,
        )

    # Create reminders for doc2 (if different)
    if doc_id2 != doc_id1:
        for i in range(2):
            reminder_data = ReminderCreate(
                date="2026-12-31",
                time="14:30",
                subject=f"Doc2 Reminder {i + 1}",
                message=f"Message {i + 1}",
                assign_user=[uuid4()],
            )

            await create_reminder(
                document_id=doc_id2,
                reminder_create=reminder_data,
                current_user=User(
                    id=uuid4(),
                    first_name="Test",
                    last_name="User",
                    username="testuser",
                    password="hashed",
                    is_active=True,
                ),
                reminder_service=reminder_service,
            )

    # Get paginated reminders for doc1 only
    result = await get_all_reminders(
        page=1,
        page_size=10,
        document_id=doc_id1,
        reminder_service=reminder_service,
    )

    assert result.total_rows == 3


@pytest.mark.asyncio
async def test_delete_reminder_success(document_service, reminder_service):
    """Test DELETE /reminders/{reminder_id} endpoint success."""
    from auth.models import User
    from core.documents.api import create_reminder
    from core.reminders.api import delete_reminder
    from core.reminders.schemas import ReminderCreate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Create reminder first
    reminder_data = ReminderCreate(
        date="2026-12-31",
        time="14:30",
        subject="Test Reminder",
        message="Test message",
        assign_user=[uuid4()],
    )

    created = await create_reminder(
        document_id=doc_id,
        reminder_create=reminder_data,
        current_user=User(
            id=uuid4(),
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        ),
        reminder_service=reminder_service,
    )

    # Delete reminder
    result = await delete_reminder(
        reminder_id=created.id,
        current_user=User(
            id=uuid4(),
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        ),
        reminder_service=reminder_service,
    )

    assert "deleted successfully" in result.detail.lower()


@pytest.mark.asyncio
async def test_delete_reminder_not_found(reminder_service):
    """Test DELETE /reminders/{reminder_id} endpoint with non-existent reminder."""
    from auth.models import User
    from core.reminders.api import delete_reminder

    non_existent_reminder_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await delete_reminder(
            reminder_id=non_existent_reminder_id,
            current_user=User(
                id=uuid4(),
                first_name="Test",
                last_name="User",
                username="testuser",
                password="hashed",
                is_active=True,
            ),
            reminder_service=reminder_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail.lower()
