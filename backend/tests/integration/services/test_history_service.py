import os
import sys
from io import BytesIO

import pytest
from fastapi import UploadFile
from sqlalchemy import select

sys.path.insert(0, f"{os.getcwd()}/src")

from configuration.models import Category, Stage, Subcategory  # noqa: E402
from core.documents.schemas import DocumentCreate  # noqa: E402
from core.documents.service import DocumentServiceImpl  # noqa: E402
from core.histories.service import HistoryServiceImpl  # noqa: E402
from core.models import Document, DocumentHistory  # noqa: E402
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
            username="testuser_hist_integration",
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


@pytest.fixture
def document_service():
    """Create a DocumentServiceImpl instance for integration testing."""
    return DocumentServiceImpl(
        unit_of_work=UnitOfWorkImpl(session_factory=default_session_factory)
    )


@pytest.fixture
def history_service():
    """Create a HistoryServiceImpl instance for integration testing."""
    return HistoryServiceImpl(
        unit_of_work=UnitOfWorkImpl(session_factory=default_session_factory)
    )


@pytest.mark.asyncio
async def test_get_document_histories_paginated_from_database(
    document_service, history_service, test_data
):
    """Test retrieving document histories with pagination from database."""
    # Create multiple documents to generate histories
    document_ids = []
    for i in range(15):
        document_data = DocumentCreate(
            name=f"History Test Document {i}",
            category_id=test_data["category_id"],
            subcategory_id=test_data["subcategory_id"],
            stage_id=test_data["stage_id"],
            assigned_to=test_data["user_id"],
        )
        upload_file = create_upload_file(f"history_{i}.pdf")
        created = await document_service.create_document(
            document_data, upload_file, test_data["user_id"]
        )
        assert not isinstance(created, Error)
        document_ids.append(created.id)

    # Get first page of document histories
    result = await history_service.get_document_histories_paginated(
        page=1, page_size=10
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 10
    assert result.total_rows >= 15
    assert result.total_pages >= 2
    assert result.current_page == 1
    assert result.has_next is True
    assert result.has_previous is False

    # Verify histories in database
    async with default_session_factory() as session:
        stmt = select(DocumentHistory).where(
            DocumentHistory.action == "Document Create"
        )
        db_result = await session.execute(stmt)
        histories = list(db_result.scalars().all())
        assert len(histories) >= 15

    # Get second page
    result_page2 = await history_service.get_document_histories_paginated(
        page=2, page_size=10
    )

    assert not isinstance(result_page2, Error)
    assert len(result_page2.data) >= 5
    assert result_page2.current_page == 2
    assert result_page2.has_previous is True


@pytest.mark.asyncio
async def test_get_document_histories_with_search_from_database(
    document_service, history_service, test_data
):
    """Test retrieving document histories with search filter from database."""
    # Create documents with specific names for searching
    archive_doc_ids = []
    for i in range(5):
        document_data = DocumentCreate(
            name=f"Document Archive Search {i}",
            category_id=test_data["category_id"],
            subcategory_id=test_data["subcategory_id"],
            stage_id=test_data["stage_id"],
            assigned_to=test_data["user_id"],
        )
        upload_file = create_upload_file(f"archive_search_{i}.pdf")
        created = await document_service.create_document(
            document_data, upload_file, test_data["user_id"]
        )
        assert not isinstance(created, Error)
        # Archive the documents to generate archive history
        await document_service.archive_document(created.id, test_data["user_id"])
        archive_doc_ids.append(created.id)

    # Create documents with different names
    for i in range(3):
        document_data = DocumentCreate(
            name=f"Document Delete Search {i}",
            category_id=test_data["category_id"],
            subcategory_id=test_data["subcategory_id"],
            stage_id=test_data["stage_id"],
            assigned_to=test_data["user_id"],
        )
        upload_file = create_upload_file(f"delete_search_{i}.pdf")
        created = await document_service.create_document(
            document_data, upload_file, test_data["user_id"]
        )
        assert not isinstance(created, Error)

    # Search for "archive" in histories
    result = await history_service.get_document_histories_paginated(
        page=1, page_size=20, search="archive"
    )

    assert not isinstance(result, Error)
    assert len(result.data) >= 5
    # Verify all results contain "archive" in action or description
    assert all(
        "archive" in h.action.lower() or "archive" in h.description.lower()
        for h in result.data
    )

    # Verify in database
    async with default_session_factory() as session:
        from sqlalchemy import or_

        stmt = select(DocumentHistory).where(
            or_(
                DocumentHistory.action.ilike("%archive%"),
                DocumentHistory.description.ilike("%archive%"),
            )
        )
        db_result = await session.execute(stmt)
        histories = list(db_result.scalars().all())
        assert len(histories) >= 5


@pytest.mark.asyncio
async def test_get_document_histories_empty_result(history_service):
    """Test retrieving document histories when none exist returns empty result."""
    result = await history_service.get_document_histories_paginated(
        page=1, page_size=10
    )

    assert not isinstance(result, Error)
    assert isinstance(result.data, list)
    assert result.current_page == 1
    assert result.page_size == 10


@pytest.mark.asyncio
async def test_get_document_histories_after_document_deletion(
    document_service, history_service, test_data
):
    """Test that document histories persist after document is deleted."""
    # Create a document
    document_data = DocumentCreate(
        name="Document to Delete with History",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("deletion_history.pdf")
    created = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )
    assert not isinstance(created, Error)
    document_id = created.id

    # Perform some actions to create history
    await document_service.archive_document(document_id, test_data["user_id"])
    await document_service.archive_document(document_id, test_data["user_id"])

    # Delete the document
    delete_result = await document_service.delete_document(
        document_id, test_data["user_id"]
    )
    assert not isinstance(delete_result, Error)

    # Verify document is deleted from database
    async with default_session_factory() as session:
        stmt = select(Document).where(Document.id == document_id)
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()
        assert db_document is None

    # Get document histories - should still exist but with null document_id
    result = await history_service.get_document_histories_paginated(
        page=1, page_size=20, search="Document to Delete with History"
    )

    assert not isinstance(result, Error)
    assert len(result.data) >= 4  # Create, Archive, Unarchive, Delete actions

    # Verify histories have null document_id and null document reference
    delete_history = [h for h in result.data if h.action == "Document Delete"]
    assert len(delete_history) >= 1
    assert delete_history[0].document_id is None
    assert delete_history[0].document is None

    # Verify in database that histories persist with null document_id
    async with default_session_factory() as session:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(DocumentHistory)
            .options(
                selectinload(DocumentHistory.document),
                selectinload(DocumentHistory.creator),
            )
            .where(
                DocumentHistory.description.ilike("%Document to Delete with History%")
            )
        )
        db_result = await session.execute(stmt)
        histories = list(db_result.scalars().all())

        assert len(histories) >= 4
        # After deletion, document_id should be NULL
        delete_histories = [h for h in histories if h.action == "Document Delete"]
        assert len(delete_histories) >= 1
        for h in delete_histories:
            assert h.document_id is None
            assert h.document is None


@pytest.mark.asyncio
async def test_get_document_histories_ordered_by_date_descending(
    document_service, history_service, test_data
):
    """Test that document histories are ordered by creation date descending."""
    import asyncio

    # Create a document
    document_data = DocumentCreate(
        name="History Order Test Document",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("history_order.pdf")
    created = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )
    assert not isinstance(created, Error)
    document_id = created.id

    # Perform sequential actions with delays to ensure different timestamps
    await asyncio.sleep(0.1)
    await document_service.archive_document(document_id, test_data["user_id"])

    await asyncio.sleep(0.1)
    await document_service.archive_document(document_id, test_data["user_id"])

    await asyncio.sleep(0.1)
    upload_file2 = create_upload_file("history_order_v2.pdf")
    await document_service.create_new_version(
        document_id, upload_file2, test_data["user_id"]
    )

    # Get document histories
    result = await history_service.get_document_histories_paginated(
        page=1, page_size=20, search="History Order Test Document"
    )

    assert not isinstance(result, Error)
    assert len(result.data) >= 4

    # Verify histories are ordered by date descending (newest first)
    for i in range(len(result.data) - 1):
        assert result.data[i].created_at >= result.data[i + 1].created_at

    # Verify in database
    async with default_session_factory() as session:
        stmt = (
            select(DocumentHistory)
            .where(DocumentHistory.document_id == document_id)
            .order_by(DocumentHistory.created_at.desc())
        )
        db_result = await session.execute(stmt)
        histories = list(db_result.scalars().all())

        assert len(histories) >= 4
        # Verify order in database
        for i in range(len(histories) - 1):
            assert histories[i].created_at >= histories[i + 1].created_at
