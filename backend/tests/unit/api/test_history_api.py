import os
import sys
from datetime import datetime
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import UploadFile

sys.path.append(f"{os.getcwd()}/src")
from auth.models import User
from core.histories.fakes import FakeHistoryService
from core.models import Document


def create_upload_file(filename: str = "test.pdf", content: bytes = b"test content"):
    """Helper to create an UploadFile for testing."""
    file = BytesIO(content)
    return UploadFile(filename=filename, file=file)


@pytest.fixture
def history_service():
    """Provide a fake history service with test data."""
    service = FakeHistoryService()

    # Create test entities for relationships
    from configuration.models import Category, Stage, Subcategory

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

    # Create test tags
    tag1_id = uuid4()
    tag2_id = uuid4()
    tag3_id = uuid4()
    service.test_tag1_id = tag1_id
    service.test_tag2_id = tag2_id
    service.test_tag3_id = tag3_id

    for i in range(15):
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name=f"Document {i}",
            category_id=category_id,
            subcategory_id=subcategory_id,
            stage_id=stage_id,
            assigned_to=user_id,
            created_by=user_id,
            description=f"Description {i}",
            archive=False,
            created_at=datetime.now(),
        )
        # Populate relationships for DocumentResponse validation
        doc.category = category
        doc.subcategory = subcategory
        doc.stage = stage
        doc.creator = user
        doc.assigned_user = user
        doc.tags = []
        service.documents[doc_id] = doc

    service.test_category_id = category_id
    service.test_subcategory_id = subcategory_id
    service.test_stage_id = stage_id
    service.test_user_id = user_id

    return service


@pytest.fixture
def current_user():
    """Provide a mock current user."""
    return User(
        id=uuid4(),
        first_name="Test",
        last_name="User",
        username="testuser",
        password="hashed",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_get_document_histories_api_success():
    """Test GET /histories endpoint."""
    from core.histories.api import get_document_histories
    from core.histories.fakes import FakeHistoryService

    history_service = FakeHistoryService()

    result = await get_document_histories(
        page=1,
        page_size=20,
        search=None,
        history_service=history_service,
    )

    assert result.current_page == 1
    assert result.total_rows == 0  # Fake service returns empty by default
    assert result.total_pages == 0
    assert len(result.data) == 0
    assert result.has_next is False
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_get_document_histories_api_with_pagination():
    """Test GET /histories endpoint with pagination."""
    from core.histories.api import get_document_histories
    from core.histories.fakes import FakeHistoryService

    history_service = FakeHistoryService()

    # Mock some histories by overriding the method
    async def mock_get_histories(page, page_size, search=None):
        from auth.users.schemas import UserBasicResponse
        from core.histories.schemas import (
            DocumentBasicResponse,
            DocumentHistoryResponse,
            PaginatedDocumentHistoryResponse,
        )

        # Create mock data
        histories = []
        for i in range(25):
            history = DocumentHistoryResponse(
                id=uuid4(),
                document_id=uuid4(),
                action=f"Action {i}",
                description=f"Description {i}",
                created_by=uuid4(),
                created_at=datetime.now(),
                document=DocumentBasicResponse(name=f"Document {i}"),
                creator=UserBasicResponse(
                    username="testuser",
                ),
            )
            histories.append(history)

        skip = (page - 1) * page_size
        paginated = histories[skip : skip + page_size]
        total_rows = len(histories)
        total_pages = (total_rows + page_size - 1) // page_size

        return PaginatedDocumentHistoryResponse(
            data=paginated,
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    history_service.get_document_histories_paginated = mock_get_histories

    # Get page 1
    result = await get_document_histories(
        page=1,
        page_size=10,
        search=None,
        history_service=history_service,
    )

    assert result.current_page == 1
    assert result.total_rows == 25
    assert result.total_pages == 3
    assert len(result.data) == 10
    assert result.has_next is True
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_get_document_histories_api_with_search():
    """Test GET /histories endpoint with search parameter."""
    from auth.users.schemas import UserBasicResponse
    from core.histories.api import get_document_histories
    from core.histories.fakes import FakeHistoryService
    from core.histories.schemas import (
        DocumentBasicResponse,
        DocumentHistoryResponse,
        PaginatedDocumentHistoryResponse,
    )

    history_service = FakeHistoryService()

    # Mock histories with search
    async def mock_get_histories(page, page_size, search=None):
        # Create mock data
        all_histories = []
        for i in range(10):
            history = DocumentHistoryResponse(
                id=uuid4(),
                document_id=uuid4(),
                action="Document Archive" if i < 5 else "Document Delete",
                description=f"Action performed {i}",
                created_by=uuid4(),
                created_at=datetime.now(),
                document=DocumentBasicResponse(name=f"Document {i}"),
                creator=UserBasicResponse(
                    username="testuser",
                ),
            )
            all_histories.append(history)

        # Filter by search if provided
        if search:
            search_lower = search.lower()
            histories = [
                h
                for h in all_histories
                if search_lower in h.action.lower()
                or search_lower in h.description.lower()
            ]
        else:
            histories = all_histories

        skip = (page - 1) * page_size
        paginated = histories[skip : skip + page_size]
        total_rows = len(histories)
        total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 0

        return PaginatedDocumentHistoryResponse(
            data=paginated,
            current_page=page,
            total_pages=total_pages,
            total_rows=total_rows,
            page_size=page_size,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    history_service.get_document_histories_paginated = mock_get_histories

    # Search for "archive"
    result = await get_document_histories(
        page=1,
        page_size=20,
        search="archive",
        history_service=history_service,
    )

    assert result.total_rows == 5
    assert all("archive" in h.action.lower() for h in result.data)
