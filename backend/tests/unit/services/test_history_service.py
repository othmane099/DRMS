import os
import sys
from datetime import datetime
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import UploadFile

sys.path.append(f"{os.getcwd()}/src")
from configuration.models import Category, Stage, Subcategory
from core.documents.service import DocumentServiceImpl
from core.histories.service import HistoryServiceImpl
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


@pytest.fixture
def history_service(uow):
    """Provide a history service with fake UoW."""
    return HistoryServiceImpl(unit_of_work=uow)


def create_upload_file(filename: str = "test.pdf", content: bytes = b"test content"):
    """Helper to create an UploadFile for testing."""
    file = BytesIO(content)
    return UploadFile(filename=filename, file=file)


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_document_histories_paginated_success(history_service, uow):
    """Test retrieving document histories with pagination."""
    from auth.models import User

    # Create a user for the creator relationship
    creator = User(
        id=uow.test_user_id,
        first_name="Test",
        last_name="Creator",
        username="testcreator",
        password="hashed",
        is_active=True,
    )

    # Create test document histories
    for i in range(15):
        history_id = uuid4()
        from core.models import DocumentHistory

        history = DocumentHistory(
            id=history_id,
            document_id=uuid4(),
            action=f"Action {i}",
            description=f"Description {i}",
            created_by=uow.test_user_id,
            created_at=datetime.now(),
        )
        history.creator = creator
        history.document = None  # Mock document
        uow.history_repository.document_histories[history_id] = history

    result = await history_service.get_document_histories_paginated(
        page=1, page_size=10
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 10
    assert result.total_rows == 15
    assert result.total_pages == 2
    assert result.current_page == 1
    assert result.has_next is True
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_get_document_histories_with_search(history_service, uow):
    """Test retrieving document histories with search filter."""
    from auth.models import User

    # Create a user for the creator relationship
    creator = User(
        id=uow.test_user_id,
        first_name="Test",
        last_name="Creator",
        username="testcreator",
        password="hashed",
        is_active=True,
    )

    # Create histories with different actions
    for i in range(5):
        history_id = uuid4()
        from core.models import DocumentHistory

        history = DocumentHistory(
            id=history_id,
            document_id=uuid4(),
            action="Document Archive",
            description=f"Document archived by user {i}",
            created_by=uow.test_user_id,
            created_at=datetime.now(),
        )
        history.creator = creator
        history.document = None
        uow.history_repository.document_histories[history_id] = history

    for i in range(3):
        history_id = uuid4()
        from core.models import DocumentHistory

        history = DocumentHistory(
            id=history_id,
            document_id=uuid4(),
            action="Document Delete",
            description=f"Document deleted by user {i}",
            created_by=uow.test_user_id,
            created_at=datetime.now(),
        )
        history.creator = creator
        history.document = None
        uow.history_repository.document_histories[history_id] = history

    # Search for "archive"
    result = await history_service.get_document_histories_paginated(
        page=1, page_size=10, search="archive"
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 5
    assert result.total_rows == 5
    assert all(
        "archive" in h.action.lower() or "archive" in h.description.lower()
        for h in result.data
    )


@pytest.mark.asyncio
async def test_get_document_histories_empty(history_service):
    """Test retrieving document histories when none exist."""
    result = await history_service.get_document_histories_paginated(
        page=1, page_size=10
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 0
    assert result.total_rows == 0
    assert result.total_pages == 0
