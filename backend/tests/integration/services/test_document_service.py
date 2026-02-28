import os
import sys
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import UploadFile
from sqlalchemy import select

sys.path.insert(0, f"{os.getcwd()}/src")

from configuration.models import Category, Stage, Subcategory  # noqa: E402
from core.documents.schemas import (
    DocumentCreate,
    DocumentFilterParams,
    ShareDocumentCreate,
)  # noqa: E402
from core.documents.service import DocumentServiceImpl  # noqa: E402
from core.models import Document, DocumentHistory, VersionHistory  # noqa: E402
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


@pytest.fixture
def document_service():
    """Create a DocumentServiceImpl instance for integration testing."""
    return DocumentServiceImpl(
        unit_of_work=UnitOfWorkImpl(session_factory=default_session_factory)
    )


@pytest.fixture
def superuser():
    """Provide a superuser that bypasses permission checks."""
    from auth.models import User

    return User(
        id=uuid4(),
        username="superuser_integration",
        password="hashed",
        is_active=True,
        is_superuser=True,
    )


@pytest.mark.asyncio
async def test_create_document_commits_to_database(document_service, test_data):
    """Test that creating a document commits data to database."""
    from sqlalchemy.orm import selectinload

    from configuration.models import Tag

    # Create tags in database first
    async with default_session_factory() as session:
        tag1 = Tag(title="integration")
        tag2 = Tag(title="test")
        session.add_all([tag1, tag2])
        await session.commit()
        await session.refresh(tag1)
        await session.refresh(tag2)
        tag_ids = [tag1.id, tag2.id]

    document_data = DocumentCreate(
        name="Integration Test Document",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
        description="Integration test description",
        tag_ids=tag_ids,
    )

    upload_file = create_upload_file(
        "integration_test.pdf", b"integration test content"
    )
    result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(result, Error)
    assert result.id is not None

    # Verify document in database with eager loading
    async with default_session_factory() as session:
        stmt = (
            select(Document)
            .options(selectinload(Document.tags))
            .where(Document.id == result.id)
        )
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()

        assert db_document is not None
        assert db_document.name == "Integration Test Document"
        assert db_document.description == "Integration test description"
        assert len(db_document.tags) == 2
        tag_titles = sorted([tag.title for tag in db_document.tags])
        assert tag_titles == ["integration", "test"]
        assert db_document.category_id == test_data["category_id"]
        assert db_document.subcategory_id == test_data["subcategory_id"]
        assert db_document.stage_id == test_data["stage_id"]
        assert db_document.assigned_to == test_data["user_id"]
        assert db_document.created_by == test_data["user_id"]


@pytest.mark.asyncio
async def test_create_document_creates_version_history(document_service, test_data):
    """Test that creating a document creates version history record."""
    document_data = DocumentCreate(
        name="Document with Version",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("version_test.pdf", b"version content")
    result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(result, Error)

    # Verify version history in database
    async with default_session_factory() as session:
        stmt = select(VersionHistory).where(VersionHistory.document_id == result.id)
        db_result = await session.execute(stmt)
        versions = list(db_result.scalars().all())

        assert len(versions) == 1
        assert versions[0].version_number == 1
        assert versions[0].is_current is True
        assert versions[0].created_by == test_data["user_id"]


@pytest.mark.asyncio
async def test_create_document_creates_document_history(document_service, test_data):
    """Test that creating a document creates document history record."""
    document_data = DocumentCreate(
        name="Document with History",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("history_test.pdf", b"history content")
    result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(result, Error)

    # Verify document history in database
    async with default_session_factory() as session:
        stmt = select(DocumentHistory).where(DocumentHistory.document_id == result.id)
        db_result = await session.execute(stmt)
        histories = list(db_result.scalars().all())

        assert len(histories) == 1
        assert histories[0].action == "Document Create"
        assert "Document with History" in histories[0].description
        assert histories[0].created_by == test_data["user_id"]


@pytest.mark.asyncio
async def test_get_documents_paginated_from_database(
    document_service, test_data, superuser
):
    """Test that getting documents retrieves from database."""
    # Create multiple documents
    for i in range(5):
        document_data = DocumentCreate(
            name=f"Paginated Document {i}",
            category_id=test_data["category_id"],
            subcategory_id=test_data["subcategory_id"],
            stage_id=test_data["stage_id"],
            assigned_to=test_data["user_id"],
        )
        upload_file = create_upload_file(f"paginated_{i}.pdf")
        await document_service.create_document(
            document_data, upload_file, test_data["user_id"]
        )

    # Get documents with pagination
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(**{"page": 1, "page_size": 3}),
        current_user=superuser,
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 3
    assert result.total_rows >= 5
    assert result.current_page == 1


@pytest.mark.asyncio
async def test_get_documents_with_category_filter_from_database(
    document_service, test_data, superuser
):
    """Test that filtering documents by category works with database."""
    # Create document with test category
    document_data = DocumentCreate(
        name="Category Filtered Document",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )
    upload_file = create_upload_file("filtered.pdf")
    created = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )
    assert not isinstance(created, Error)

    # Get documents filtered by category
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(
            **{"page": 1, "page_size": 10, "category_id": test_data["category_id"]}
        ),
        current_user=superuser,
    )

    assert not isinstance(result, Error)
    assert all(d.category_id == test_data["category_id"] for d in result.data)


@pytest.mark.asyncio
async def test_create_document_with_tags_stores_correctly(document_service, test_data):
    """Test that document tags are stored correctly in database."""
    from sqlalchemy.orm import selectinload

    from configuration.models import Tag

    # First create tags in database
    async with default_session_factory() as session:
        tag1 = Tag(title="python")
        tag2 = Tag(title="fastapi")
        tag3 = Tag(title="sqlalchemy")
        session.add_all([tag1, tag2, tag3])
        await session.commit()
        await session.refresh(tag1)
        await session.refresh(tag2)
        await session.refresh(tag3)
        tag_ids = [tag1.id, tag2.id, tag3.id]

    document_data = DocumentCreate(
        name="Tagged Document",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
        tag_ids=tag_ids,
    )

    upload_file = create_upload_file("tagged.pdf")
    result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(result, Error)

    # Verify tags in database with eager loading
    async with default_session_factory() as session:
        stmt = (
            select(Document)
            .options(selectinload(Document.tags))
            .where(Document.id == result.id)
        )
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()

        assert db_document is not None
        assert len(db_document.tags) == 3
        tag_titles = sorted([tag.title for tag in db_document.tags])
        assert tag_titles == ["fastapi", "python", "sqlalchemy"]


@pytest.mark.asyncio
async def test_delete_document_success(document_service, test_data):
    """Test that deleting a document removes it from database."""

    from configuration.models import Tag

    # Create tags in database first
    async with default_session_factory() as session:
        tag1 = Tag(title="delete-test")
        session.add(tag1)
        await session.commit()
        await session.refresh(tag1)
        tag_id = tag1.id

    # Create a document
    document_data = DocumentCreate(
        name="Document to Delete",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
        description="Will be deleted",
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("delete_test.pdf")
    result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(result, Error)
    document_id = result.id

    # Verify document exists in database
    async with default_session_factory() as session:
        stmt = select(Document).where(Document.id == document_id)
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()
        assert db_document is not None

    # Delete the document
    delete_result = await document_service.delete_document(
        document_id, test_data["user_id"]
    )

    assert not isinstance(delete_result, Error)
    assert delete_result.detail == "Document deleted successfully"

    # Verify document is deleted from database
    async with default_session_factory() as session:
        stmt = select(Document).where(Document.id == document_id)
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()
        assert db_document is None

    # Verify version histories are also deleted
    async with default_session_factory() as session:
        stmt = select(VersionHistory).where(VersionHistory.document_id == document_id)
        db_result = await session.execute(stmt)
        versions = db_result.scalars().all()
        assert len(versions) == 0


@pytest.mark.asyncio
async def test_delete_document_not_found(document_service, test_data):
    """Test deleting a non-existent document returns error."""
    non_existent_id = uuid4()

    result = await document_service.delete_document(
        non_existent_id, test_data["user_id"]
    )

    assert isinstance(result, Error)
    assert result.code == 404
    assert result.detail == "Document not found"


@pytest.mark.asyncio
async def test_delete_document_creates_history(document_service, test_data):
    """Test that deleting a document creates a history entry."""
    # Create a document
    document_data = DocumentCreate(
        name="Document with History",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
        description="Testing history",
    )

    upload_file = create_upload_file("history_test.pdf")
    result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(result, Error)
    document_id = result.id

    # Delete the document
    delete_result = await document_service.delete_document(
        document_id, test_data["user_id"]
    )

    assert not isinstance(delete_result, Error)

    # Verify history entry was created (even though document is deleted)
    # Note: document_id will be NULL after deletion due to ondelete="SET NULL"
    async with default_session_factory() as session:
        stmt = (
            select(DocumentHistory)
            .where(DocumentHistory.action == "Document Delete")
            .where(DocumentHistory.created_by == test_data["user_id"])
            .order_by(DocumentHistory.created_at.desc())
        )
        db_result = await session.execute(stmt)
        history_entry = db_result.scalars().first()
        assert history_entry is not None
        assert "deleted" in history_entry.description
        assert "Document with History" in history_entry.description
        # document_id should be NULL after document deletion
        assert history_entry.document_id is None


@pytest.mark.asyncio
async def test_get_document_by_id_success(document_service, test_data):
    """Test retrieving a document by ID from database."""
    from sqlalchemy.orm import selectinload

    from configuration.models import Tag

    # Create tags in database first
    async with default_session_factory() as session:
        tag1 = Tag(title="get-test")
        tag2 = Tag(title="retrieve")
        session.add_all([tag1, tag2])
        await session.commit()
        await session.refresh(tag1)
        await session.refresh(tag2)
        tag_ids = [tag1.id, tag2.id]

    # Create a document
    document_data = DocumentCreate(
        name="Document to Retrieve",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
        description="Testing get by ID",
        tag_ids=tag_ids,
    )

    upload_file = create_upload_file("retrieve_test.pdf")
    created = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created, Error)
    document_id = created.id

    # Retrieve the document by ID
    result = await document_service.get_document_by_id(document_id)

    # Verify successful retrieval
    assert not isinstance(result, Error)
    assert result.id == document_id
    assert result.name == "Document to Retrieve"
    assert result.description == "Testing get by ID"
    assert result.category_id == test_data["category_id"]
    assert result.subcategory_id == test_data["subcategory_id"]
    assert result.stage_id == test_data["stage_id"]
    assert result.assigned_to == test_data["user_id"]
    assert result.created_by == test_data["user_id"]
    assert len(result.tags) == 2

    # Verify document exists in database with proper relationships
    async with default_session_factory() as session:
        stmt = (
            select(Document)
            .options(selectinload(Document.tags))
            .where(Document.id == document_id)
        )
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()

        assert db_document is not None
        assert db_document.name == "Document to Retrieve"
        assert db_document.description == "Testing get by ID"
        assert len(db_document.tags) == 2
        tag_titles = sorted([tag.title for tag in db_document.tags])
        assert tag_titles == ["get-test", "retrieve"]


@pytest.mark.asyncio
async def test_get_document_by_id_not_found(document_service):
    """Test retrieving a non-existent document by ID."""
    non_existent_id = uuid4()

    result = await document_service.get_document_by_id(non_existent_id)

    assert isinstance(result, Error)
    assert result.code == 404
    assert result.detail == "Document not found"


@pytest.mark.asyncio
async def test_get_version_history_success(document_service, test_data):
    """Test retrieving version history from database."""
    from configuration.models import Tag

    # Create tags in database first
    async with default_session_factory() as session:
        tag1 = Tag(title="version-test")
        session.add(tag1)
        await session.commit()
        await session.refresh(tag1)
        tag_id = tag1.id

    # Create a document
    document_data = DocumentCreate(
        name="Document with Version History",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
        description="Testing version history",
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("version_history_test.pdf", b"version content")
    result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(result, Error)
    document_id = result.id

    # Get version history
    versions_result = await document_service.get_version_history(document_id)

    # Verify version history retrieved
    assert not isinstance(versions_result, Error)
    assert isinstance(versions_result, list)
    assert len(versions_result) == 1
    assert versions_result[0].document_id == document_id
    assert versions_result[0].version_number == 1
    assert versions_result[0].is_current is True
    assert versions_result[0].created_by == test_data["user_id"]

    # Verify version history exists in database
    async with default_session_factory() as session:
        stmt = select(VersionHistory).where(VersionHistory.document_id == document_id)
        db_result = await session.execute(stmt)
        db_versions = list(db_result.scalars().all())

        assert len(db_versions) == 1
        assert db_versions[0].version_number == 1
        assert db_versions[0].is_current is True


@pytest.mark.asyncio
async def test_get_version_history_not_found(document_service):
    """Test retrieving version history for non-existent document."""
    non_existent_id = uuid4()

    result = await document_service.get_version_history(non_existent_id)

    assert isinstance(result, Error)
    assert result.code == 404
    assert result.detail == "Document not found"


@pytest.mark.asyncio
async def test_get_version_history_ordered_by_date(document_service, test_data):
    """Test that version history is ordered by creation date descending."""
    import asyncio

    # Create a document
    document_data = DocumentCreate(
        name="Document with Multiple Versions",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("multi_version.pdf", b"version 1 content")
    result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(result, Error)
    document_id = result.id

    # Create additional versions manually in database
    async with default_session_factory() as session:
        # Add a small delay to ensure different timestamps
        await asyncio.sleep(0.1)

        version2 = VersionHistory(
            document_id=document_id,
            document_file=f"uploads/documents/{document_id}_v2.pdf",
            version_number=2,
            is_current=False,
            created_by=test_data["user_id"],
        )
        session.add(version2)
        await session.flush()

        await asyncio.sleep(0.1)

        version3 = VersionHistory(
            document_id=document_id,
            document_file=f"uploads/documents/{document_id}_v3.pdf",
            version_number=3,
            is_current=False,
            created_by=test_data["user_id"],
        )
        session.add(version3)
        await session.commit()

    # Get version history
    versions_result = await document_service.get_version_history(document_id)

    # Verify versions are ordered newest first
    assert not isinstance(versions_result, Error)
    assert len(versions_result) == 3
    # Version 3 should be first (newest)
    assert versions_result[0].version_number == 3
    assert versions_result[1].version_number == 2
    assert versions_result[2].version_number == 1


@pytest.mark.asyncio
async def test_create_new_version_success(document_service, test_data):
    """Test creating a new version persists to database."""
    # Create a document
    document_data = DocumentCreate(
        name="Document for New Version Test",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file1 = create_upload_file("version1.pdf", b"version 1 content")
    result = await document_service.create_document(
        document_data, upload_file1, test_data["user_id"]
    )

    assert not isinstance(result, Error)
    document_id = result.id

    # Verify initial version in database
    async with default_session_factory() as session:
        stmt = select(VersionHistory).where(VersionHistory.document_id == document_id)
        db_result = await session.execute(stmt)
        versions = list(db_result.scalars().all())
        assert len(versions) == 1
        assert versions[0].version_number == 1
        assert versions[0].is_current is True

    # Create new version
    upload_file2 = create_upload_file("version2.pdf", b"version 2 content")
    new_version_result = await document_service.create_new_version(
        document_id, upload_file2, test_data["user_id"]
    )

    assert not isinstance(new_version_result, Error)
    assert new_version_result.version_number == 2
    assert new_version_result.is_current is True

    # Verify in database
    async with default_session_factory() as session:
        stmt = (
            select(VersionHistory)
            .where(VersionHistory.document_id == document_id)
            .order_by(VersionHistory.version_number.desc())
        )
        db_result = await session.execute(stmt)
        versions = list(db_result.scalars().all())

        assert len(versions) == 2
        # Version 2 should be current
        assert versions[0].version_number == 2
        assert versions[0].is_current is True
        # Version 1 should not be current
        assert versions[1].version_number == 1
        assert versions[1].is_current is False


@pytest.mark.asyncio
async def test_create_new_version_creates_history(document_service, test_data):
    """Test that creating a new version creates document history entry."""
    # Create a document
    document_data = DocumentCreate(
        name="Document Version History Test",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file1 = create_upload_file("version1.pdf", b"version 1 content")
    result = await document_service.create_document(
        document_data, upload_file1, test_data["user_id"]
    )

    assert not isinstance(result, Error)
    document_id = result.id

    # Create new version
    upload_file2 = create_upload_file("version2.pdf", b"version 2 content")
    new_version_result = await document_service.create_new_version(
        document_id, upload_file2, test_data["user_id"]
    )

    assert not isinstance(new_version_result, Error)

    # Verify document history entry created
    async with default_session_factory() as session:
        stmt = (
            select(DocumentHistory)
            .where(DocumentHistory.document_id == document_id)
            .where(DocumentHistory.action == "New Version")
            .order_by(DocumentHistory.created_at.desc())
        )
        db_result = await session.execute(stmt)
        history_entry = db_result.scalars().first()

        assert history_entry is not None
        assert "New version uploaded" in history_entry.description
        assert "Document Version History Test" in history_entry.description
        assert history_entry.created_by == test_data["user_id"]


@pytest.mark.asyncio
async def test_create_new_version_not_found(document_service):
    """Test creating version for non-existent document."""
    non_existent_id = uuid4()
    upload_file = create_upload_file("test.pdf")

    result = await document_service.create_new_version(
        non_existent_id, upload_file, uuid4()
    )

    assert isinstance(result, Error)
    assert result.code == 404
    assert result.detail == "Document not found"


@pytest.mark.asyncio
async def test_create_new_version_multiple_sequential(document_service, test_data):
    """Test creating multiple versions sequentially."""
    # Create a document
    document_data = DocumentCreate(
        name="Document Multiple Sequential Versions",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file1 = create_upload_file("v1.pdf", b"version 1")
    result = await document_service.create_document(
        document_data, upload_file1, test_data["user_id"]
    )

    assert not isinstance(result, Error)
    document_id = result.id

    # Create version 2
    upload_file2 = create_upload_file("v2.pdf", b"version 2")
    version2 = await document_service.create_new_version(
        document_id, upload_file2, test_data["user_id"]
    )
    assert not isinstance(version2, Error)
    assert version2.version_number == 2

    # Create version 3
    upload_file3 = create_upload_file("v3.pdf", b"version 3")
    version3 = await document_service.create_new_version(
        document_id, upload_file3, test_data["user_id"]
    )
    assert not isinstance(version3, Error)
    assert version3.version_number == 3

    # Verify all versions in database
    async with default_session_factory() as session:
        stmt = (
            select(VersionHistory)
            .where(VersionHistory.document_id == document_id)
            .order_by(VersionHistory.version_number.desc())
        )
        db_result = await session.execute(stmt)
        versions = list(db_result.scalars().all())

        assert len(versions) == 3
        assert versions[0].version_number == 3
        assert versions[0].is_current is True
        assert versions[1].version_number == 2
        assert versions[1].is_current is False
        assert versions[2].version_number == 1
        assert versions[2].is_current is False


@pytest.mark.asyncio
async def test_archive_document_commits_to_database(document_service, test_data):
    """Test that archiving a document commits the change to database."""
    from sqlalchemy.orm import selectinload

    # Create a document
    document_data = DocumentCreate(
        name="Document to Archive Integration",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("archive_integration.pdf")
    result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(result, Error)
    document_id = result.id

    # Verify document is not archived initially in database
    async with default_session_factory() as session:
        stmt = select(Document).where(Document.id == document_id)
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()
        assert db_document is not None
        assert db_document.archive is False

    # Archive the document
    archive_result = await document_service.archive_document(
        document_id, test_data["user_id"]
    )

    assert not isinstance(archive_result, Error)
    assert archive_result.archive is True

    # Verify document is archived in database
    async with default_session_factory() as session:
        stmt = (
            select(Document)
            .options(
                selectinload(Document.stage),
                selectinload(Document.assigned_user),
                selectinload(Document.creator),
                selectinload(Document.category),
                selectinload(Document.subcategory),
                selectinload(Document.tags),
            )
            .where(Document.id == document_id)
        )
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()
        assert db_document is not None
        assert db_document.archive is True


@pytest.mark.asyncio
async def test_archive_document_toggle_persists(document_service, test_data):
    """Test that toggling archive status persists correctly to database."""
    # Create a document
    document_data = DocumentCreate(
        name="Document to Toggle Archive",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("toggle_archive.pdf")
    result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(result, Error)
    document_id = result.id

    # Archive the document (first toggle)
    archive_result1 = await document_service.archive_document(
        document_id, test_data["user_id"]
    )
    assert not isinstance(archive_result1, Error)
    assert archive_result1.archive is True

    # Verify in database
    async with default_session_factory() as session:
        stmt = select(Document).where(Document.id == document_id)
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()
        assert db_document.archive is True

    # Unarchive the document (second toggle)
    archive_result2 = await document_service.archive_document(
        document_id, test_data["user_id"]
    )
    assert not isinstance(archive_result2, Error)
    assert archive_result2.archive is False

    # Verify in database
    async with default_session_factory() as session:
        stmt = select(Document).where(Document.id == document_id)
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()
        assert db_document.archive is False

    # Archive again (third toggle)
    archive_result3 = await document_service.archive_document(
        document_id, test_data["user_id"]
    )
    assert not isinstance(archive_result3, Error)
    assert archive_result3.archive is True

    # Verify in database
    async with default_session_factory() as session:
        stmt = select(Document).where(Document.id == document_id)
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()
        assert db_document.archive is True


@pytest.mark.asyncio
async def test_archive_document_creates_history(document_service, test_data):
    """Test that archiving a document creates a history entry in database."""
    # Create a document
    document_data = DocumentCreate(
        name="Document Archive History Test",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("archive_history.pdf")
    result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(result, Error)
    document_id = result.id

    # Archive the document
    archive_result = await document_service.archive_document(
        document_id, test_data["user_id"]
    )
    assert not isinstance(archive_result, Error)

    # Verify document history entry created in database
    async with default_session_factory() as session:
        stmt = (
            select(DocumentHistory)
            .where(DocumentHistory.document_id == document_id)
            .where(DocumentHistory.action == "Document Archive")
            .order_by(DocumentHistory.created_at.desc())
        )
        db_result = await session.execute(stmt)
        history_entry = db_result.scalars().first()

        assert history_entry is not None
        assert "archived" in history_entry.description.lower()
        assert "Document Archive History Test" in history_entry.description
        assert history_entry.created_by == test_data["user_id"]


@pytest.mark.asyncio
async def test_unarchive_document_creates_history(document_service, test_data):
    """Test that unarchiving a document creates a history entry in database."""
    # Create a document
    document_data = DocumentCreate(
        name="Document Unarchive History Test",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("unarchive_history.pdf")
    result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(result, Error)
    document_id = result.id

    # Archive the document first
    await document_service.archive_document(document_id, test_data["user_id"])

    # Unarchive the document
    unarchive_result = await document_service.archive_document(
        document_id, test_data["user_id"]
    )
    assert not isinstance(unarchive_result, Error)
    assert unarchive_result.archive is False

    # Verify document history entry created in database
    async with default_session_factory() as session:
        stmt = (
            select(DocumentHistory)
            .where(DocumentHistory.document_id == document_id)
            .where(DocumentHistory.action == "Document Unarchive")
            .order_by(DocumentHistory.created_at.desc())
        )
        db_result = await session.execute(stmt)
        history_entry = db_result.scalars().first()

        assert history_entry is not None
        assert "unarchived" in history_entry.description.lower()
        assert "Document Unarchive History Test" in history_entry.description
        assert history_entry.created_by == test_data["user_id"]


@pytest.mark.asyncio
async def test_archive_document_not_found(document_service, test_data):
    """Test archiving a non-existent document returns error."""
    non_existent_id = uuid4()

    result = await document_service.archive_document(
        non_existent_id, test_data["user_id"]
    )

    assert isinstance(result, Error)
    assert result.code == 404
    assert result.detail == "Document not found"


@pytest.mark.asyncio
async def test_get_documents_excludes_archived_by_default(
    document_service, test_data, superuser
):
    """Test that get_documents excludes archived documents by default."""
    # Create non-archived documents
    for i in range(3):
        document_data = DocumentCreate(
            name=f"Non-Archived Integration {i}",
            category_id=test_data["category_id"],
            subcategory_id=test_data["subcategory_id"],
            stage_id=test_data["stage_id"],
            assigned_to=test_data["user_id"],
        )
        upload_file = create_upload_file(f"non_archived_{i}.pdf")
        await document_service.create_document(
            document_data, upload_file, test_data["user_id"]
        )

    # Create and archive documents
    archived_ids = []
    for i in range(2):
        document_data = DocumentCreate(
            name=f"Archived Integration {i}",
            category_id=test_data["category_id"],
            subcategory_id=test_data["subcategory_id"],
            stage_id=test_data["stage_id"],
            assigned_to=test_data["user_id"],
        )
        upload_file = create_upload_file(f"archived_{i}.pdf")
        created = await document_service.create_document(
            document_data, upload_file, test_data["user_id"]
        )
        # Archive the document
        await document_service.archive_document(created.id, test_data["user_id"])
        archived_ids.append(created.id)

    # Get documents without specifying archive parameter (should default to False)
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(**{"page": 1, "page_size": 10}),
        current_user=superuser,
    )

    assert not isinstance(result, Error)
    # Verify all returned documents are not archived
    assert all(doc.archive is False for doc in result.data)
    # Verify archived documents are not in the results
    result_ids = [doc.id for doc in result.data]
    for archived_id in archived_ids:
        assert archived_id not in result_ids

    # Verify in database that archived documents exist but are not returned
    async with default_session_factory() as session:
        stmt = select(Document).where(Document.archive == True)  # noqa: E712
        db_result = await session.execute(stmt)
        archived_docs = list(db_result.scalars().all())
        assert len(archived_docs) >= 2


@pytest.mark.asyncio
async def test_get_documents_with_archive_true(document_service, test_data, superuser):
    """Test that get_documents returns only archived documents when archive=True."""
    # Create non-archived documents
    for i in range(2):
        document_data = DocumentCreate(
            name=f"Non-Archived Filter Test {i}",
            category_id=test_data["category_id"],
            subcategory_id=test_data["subcategory_id"],
            stage_id=test_data["stage_id"],
            assigned_to=test_data["user_id"],
        )
        upload_file = create_upload_file(f"non_archived_filter_{i}.pdf")
        await document_service.create_document(
            document_data, upload_file, test_data["user_id"]
        )

    # Create and archive documents
    archived_ids = []
    for i in range(3):
        document_data = DocumentCreate(
            name=f"Archived Filter Test {i}",
            category_id=test_data["category_id"],
            subcategory_id=test_data["subcategory_id"],
            stage_id=test_data["stage_id"],
            assigned_to=test_data["user_id"],
        )
        upload_file = create_upload_file(f"archived_filter_{i}.pdf")
        created = await document_service.create_document(
            document_data, upload_file, test_data["user_id"]
        )
        # Archive the document
        await document_service.archive_document(created.id, test_data["user_id"])
        archived_ids.append(created.id)

    # Get only archived documents
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(**{"page": 1, "page_size": 10, "archive": True}),
        current_user=superuser,
    )

    assert not isinstance(result, Error)
    # Verify all returned documents are archived
    assert all(doc.archive is True for doc in result.data)
    # Verify our archived documents are in the results
    result_ids = [doc.id for doc in result.data]
    for archived_id in archived_ids:
        assert archived_id in result_ids

    # Verify in database
    async with default_session_factory() as session:
        stmt = select(Document).where(Document.archive == True)  # noqa: E712
        db_result = await session.execute(stmt)
        archived_docs = list(db_result.scalars().all())
        assert len(archived_docs) >= 3


@pytest.mark.asyncio
async def test_get_documents_archive_filter_with_category(
    document_service, test_data, superuser
):
    """Test that archive filter works with other filters like category."""
    # Create a second category
    from configuration.models import Category, Subcategory

    async with default_session_factory() as session:
        category2 = Category(title="Second Category")
        session.add(category2)
        await session.flush()

        subcategory2 = Subcategory(title="Second Subcategory", category_id=category2.id)
        session.add(subcategory2)
        await session.commit()
        await session.refresh(category2)
        await session.refresh(subcategory2)
        category2_id = category2.id
        subcategory2_id = subcategory2.id

    # Create documents in first category (archived and non-archived)
    for i in range(2):
        document_data = DocumentCreate(
            name=f"Cat1 Non-Archived {i}",
            category_id=test_data["category_id"],
            subcategory_id=test_data["subcategory_id"],
            stage_id=test_data["stage_id"],
            assigned_to=test_data["user_id"],
        )
        upload_file = create_upload_file(f"cat1_non_archived_{i}.pdf")
        await document_service.create_document(
            document_data, upload_file, test_data["user_id"]
        )

    archived_cat1_ids = []
    for i in range(2):
        document_data = DocumentCreate(
            name=f"Cat1 Archived {i}",
            category_id=test_data["category_id"],
            subcategory_id=test_data["subcategory_id"],
            stage_id=test_data["stage_id"],
            assigned_to=test_data["user_id"],
        )
        upload_file = create_upload_file(f"cat1_archived_{i}.pdf")
        created = await document_service.create_document(
            document_data, upload_file, test_data["user_id"]
        )
        await document_service.archive_document(created.id, test_data["user_id"])
        archived_cat1_ids.append(created.id)

    # Create documents in second category (archived)
    for i in range(2):
        document_data = DocumentCreate(
            name=f"Cat2 Archived {i}",
            category_id=category2_id,
            subcategory_id=subcategory2_id,
            stage_id=test_data["stage_id"],
            assigned_to=test_data["user_id"],
        )
        upload_file = create_upload_file(f"cat2_archived_{i}.pdf")
        created = await document_service.create_document(
            document_data, upload_file, test_data["user_id"]
        )
        await document_service.archive_document(created.id, test_data["user_id"])

    # Get archived documents from first category only
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(
            **{
                "page": 1,
                "page_size": 10,
                "archive": True,
                "category_id": test_data["category_id"],
            }
        ),
        current_user=superuser,
    )

    assert not isinstance(result, Error)
    # Verify all returned documents are archived and from first category
    assert all(doc.archive is True for doc in result.data)
    assert all(doc.category_id == test_data["category_id"] for doc in result.data)
    # Verify our archived documents from cat1 are in the results
    result_ids = [doc.id for doc in result.data]
    for archived_id in archived_cat1_ids:
        assert archived_id in result_ids


@pytest.mark.asyncio
async def test_create_comment_commits_to_database(document_service, test_data):
    """Test that creating a comment commits data to database."""
    from sqlalchemy.orm import selectinload

    from core.documents.schemas import DocumentCommentCreate
    from core.models import DocumentComment

    # Create a document
    document_data = DocumentCreate(
        name="Document for Comment Integration",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("comment_integration.pdf")
    document_result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(document_result, Error)
    document_id = document_result.id

    # Create a comment
    comment_create = DocumentCommentCreate(
        comment="This is an integration test comment"
    )
    result = await document_service.create_comment(
        document_id=document_id,
        comment_create=comment_create,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(result, Error)
    assert result.comment == "This is an integration test comment"
    assert result.document_id == document_id
    assert result.user_id == test_data["user_id"]
    comment_id = result.id

    # Verify comment in database
    async with default_session_factory() as session:
        stmt = (
            select(DocumentComment)
            .options(selectinload(DocumentComment.user))
            .where(DocumentComment.id == comment_id)
        )
        db_result = await session.execute(stmt)
        db_comment = db_result.scalar_one_or_none()

        assert db_comment is not None
        assert db_comment.comment == "This is an integration test comment"
        assert db_comment.document_id == document_id
        assert db_comment.user_id == test_data["user_id"]
        assert db_comment.user is not None


@pytest.mark.asyncio
async def test_create_comment_creates_document_history(document_service, test_data):
    """Test that creating a comment creates document history entry."""
    from core.documents.schemas import DocumentCommentCreate

    # Create a document
    document_data = DocumentCreate(
        name="Document Comment History Test",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("comment_history.pdf")
    document_result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(document_result, Error)
    document_id = document_result.id

    # Create a comment
    comment_create = DocumentCommentCreate(comment="Test comment for history")
    result = await document_service.create_comment(
        document_id=document_id,
        comment_create=comment_create,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(result, Error)

    # Verify document history entry created in database
    async with default_session_factory() as session:
        stmt = (
            select(DocumentHistory)
            .where(DocumentHistory.document_id == document_id)
            .where(DocumentHistory.action == "Comment Create")
            .order_by(DocumentHistory.created_at.desc())
        )
        db_result = await session.execute(stmt)
        history_entry = db_result.scalars().first()

        assert history_entry is not None
        assert "comment created" in history_entry.description.lower()
        assert "Document Comment History Test" in history_entry.description
        assert history_entry.created_by == test_data["user_id"]


@pytest.mark.asyncio
async def test_create_comment_document_not_found(document_service, test_data):
    """Test creating a comment on non-existent document returns error."""
    from core.documents.schemas import DocumentCommentCreate

    non_existent_id = uuid4()
    comment_create = DocumentCommentCreate(comment="Test comment")

    result = await document_service.create_comment(
        document_id=non_existent_id,
        comment_create=comment_create,
        current_user_id=test_data["user_id"],
    )

    assert isinstance(result, Error)
    assert result.code == 404
    assert result.detail == "Document not found"


@pytest.mark.asyncio
async def test_create_multiple_comments_on_same_document(document_service, test_data):
    """Test creating multiple comments on the same document persists correctly."""
    from sqlalchemy.orm import selectinload

    from core.documents.schemas import DocumentCommentCreate
    from core.models import DocumentComment

    # Create a document
    document_data = DocumentCreate(
        name="Document for Multiple Comments",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("multiple_comments.pdf")
    document_result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(document_result, Error)
    document_id = document_result.id

    # Create first comment
    comment1_create = DocumentCommentCreate(comment="First comment")
    result1 = await document_service.create_comment(
        document_id=document_id,
        comment_create=comment1_create,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(result1, Error)
    comment1_id = result1.id

    # Create second comment
    comment2_create = DocumentCommentCreate(comment="Second comment")
    result2 = await document_service.create_comment(
        document_id=document_id,
        comment_create=comment2_create,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(result2, Error)
    comment2_id = result2.id

    # Create third comment
    comment3_create = DocumentCommentCreate(comment="Third comment")
    result3 = await document_service.create_comment(
        document_id=document_id,
        comment_create=comment3_create,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(result3, Error)
    comment3_id = result3.id

    # Verify all comments exist in database
    async with default_session_factory() as session:
        stmt = (
            select(DocumentComment)
            .options(selectinload(DocumentComment.user))
            .where(DocumentComment.document_id == document_id)
            .order_by(DocumentComment.created_at)
        )
        db_result = await session.execute(stmt)
        comments = list(db_result.scalars().all())

        assert len(comments) == 3
        assert comments[0].id == comment1_id
        assert comments[0].comment == "First comment"
        assert comments[1].id == comment2_id
        assert comments[1].comment == "Second comment"
        assert comments[2].id == comment3_id
        assert comments[2].comment == "Third comment"


@pytest.mark.asyncio
async def test_create_comment_long_text(document_service, test_data):
    """Test creating a comment with long text persists correctly."""
    from core.documents.schemas import DocumentCommentCreate
    from core.models import DocumentComment

    # Create a document
    document_data = DocumentCreate(
        name="Document for Long Comment",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("long_comment.pdf")
    document_result = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(document_result, Error)
    document_id = document_result.id

    # Create a long comment
    long_comment = "This is a very long comment. " * 100
    comment_create = DocumentCommentCreate(comment=long_comment)
    result = await document_service.create_comment(
        document_id=document_id,
        comment_create=comment_create,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(result, Error)
    comment_id = result.id

    # Verify long comment in database
    async with default_session_factory() as session:
        stmt = select(DocumentComment).where(DocumentComment.id == comment_id)
        db_result = await session.execute(stmt)
        db_comment = db_result.scalar_one_or_none()

        assert db_comment is not None
        assert db_comment.comment == long_comment
        assert len(db_comment.comment) == len(long_comment)


@pytest.mark.asyncio
async def test_get_document_comments_retrieves_from_database(
    document_service, test_data
):
    """Test that getting comments retrieves data from database."""
    from configuration.models import Tag
    from core.documents.schemas import DocumentCommentCreate
    from core.models import DocumentComment

    # Create tags in database first
    async with default_session_factory() as session:
        tag = Tag(title="comment-test")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)
        tag_id = tag.id

    # Create document
    document_data = DocumentCreate(
        name="Document for Get Comments Test",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("get_comments_test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Create multiple comments
    comment1_create = DocumentCommentCreate(comment="First comment")
    await document_service.create_comment(
        document_id=document_id,
        comment_create=comment1_create,
        current_user_id=test_data["user_id"],
    )

    comment2_create = DocumentCommentCreate(comment="Second comment")
    await document_service.create_comment(
        document_id=document_id,
        comment_create=comment2_create,
        current_user_id=test_data["user_id"],
    )

    comment3_create = DocumentCommentCreate(comment="Third comment")
    await document_service.create_comment(
        document_id=document_id,
        comment_create=comment3_create,
        current_user_id=test_data["user_id"],
    )

    # Get comments
    result = await document_service.get_document_comments(document_id=document_id)

    # Verify comments retrieved
    assert not isinstance(result, Error)
    assert isinstance(result, list)
    assert len(result) == 3

    # Verify comments are ordered by created_at ascending (oldest first)
    assert result[0].comment == "First comment"
    assert result[1].comment == "Second comment"
    assert result[2].comment == "Third comment"

    # Verify all comments have correct document_id
    assert all(c.document_id == document_id for c in result)

    # Verify all comments have user relationship populated
    assert all(c.user is not None for c in result)
    assert all(c.user_id == test_data["user_id"] for c in result)

    # Verify comments exist in database
    async with default_session_factory() as session:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(DocumentComment)
            .options(selectinload(DocumentComment.user))
            .where(DocumentComment.document_id == document_id)
            .order_by(DocumentComment.created_at)
        )
        db_result = await session.execute(stmt)
        db_comments = list(db_result.scalars().all())

        assert len(db_comments) == 3
        assert db_comments[0].comment == "First comment"
        assert db_comments[1].comment == "Second comment"
        assert db_comments[2].comment == "Third comment"


@pytest.mark.asyncio
async def test_get_document_comments_empty(document_service, test_data):
    """Test getting comments when no comments exist."""
    from configuration.models import Tag

    # Create tags in database first
    async with default_session_factory() as session:
        tag = Tag(title="empty-comments-test")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)
        tag_id = tag.id

    # Create document without comments
    document_data = DocumentCreate(
        name="Document No Comments Integration",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("no_comments.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Get comments (should be empty)
    result = await document_service.get_document_comments(document_id=document_id)

    # Should return empty list
    assert not isinstance(result, Error)
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_document_comments_document_not_found(document_service):
    """Test getting comments for non-existent document."""
    non_existent_id = uuid4()

    result = await document_service.get_document_comments(document_id=non_existent_id)

    assert isinstance(result, Error)
    assert result.code == 404
    assert result.detail == "Document not found"


@pytest.mark.asyncio
async def test_get_document_comments_ordering(document_service, test_data):
    """Test that comments are returned in created_at ascending order."""
    import asyncio

    from configuration.models import Tag
    from core.documents.schemas import DocumentCommentCreate
    from core.models import DocumentComment

    # Create tags in database first
    async with default_session_factory() as session:
        tag = Tag(title="ordering-test")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)
        tag_id = tag.id

    # Create document
    document_data = DocumentCreate(
        name="Document Comment Ordering Test",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("ordering_test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Create multiple comments with delays to ensure different timestamps
    for i in range(5):
        comment_create = DocumentCommentCreate(comment=f"Comment {i}")
        await document_service.create_comment(
            document_id=document_id,
            comment_create=comment_create,
            current_user_id=test_data["user_id"],
        )
        # Small delay to ensure different created_at timestamps
        await asyncio.sleep(0.01)

    # Get comments
    result = await document_service.get_document_comments(document_id=document_id)

    # Verify comments are ordered by created_at ascending
    assert not isinstance(result, Error)
    assert len(result) == 5

    for i in range(5):
        assert result[i].comment == f"Comment {i}"

    # Verify timestamps are in ascending order
    for i in range(len(result) - 1):
        assert result[i].created_at <= result[i + 1].created_at

    # Verify in database
    async with default_session_factory() as session:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(DocumentComment)
            .options(selectinload(DocumentComment.user))
            .where(DocumentComment.document_id == document_id)
            .order_by(DocumentComment.created_at)
        )
        db_result = await session.execute(stmt)
        db_comments = list(db_result.scalars().all())

        assert len(db_comments) == 5
        for i in range(5):
            assert db_comments[i].comment == f"Comment {i}"


@pytest.mark.asyncio
async def test_share_document_commits_to_database(document_service, test_data):
    """Test that sharing a document commits data to database."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User
    from core.models import ShareDocument

    # Create users to share with
    async with default_session_factory() as session:
        user1 = User(
            first_name="Share",
            last_name="User1",
            username="share_user1_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        user2 = User(
            first_name="Share",
            last_name="User2",
            username="share_user2_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add_all([user1, user2])
        await session.commit()
        await session.refresh(user1)
        await session.refresh(user2)
        user1_id = user1.id
        user2_id = user2.id

    # Create a document
    document_data = DocumentCreate(
        name="Document to Share Integration",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("share_integration.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Share the document
    share_data = ShareDocumentCreate(
        user_ids=[user1_id, user2_id],
        start_date="2024-01-01",
        end_date="2024-12-31",
    )

    result = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=test_data["user_id"],
    )

    # Verify shares created
    assert not isinstance(result, Error)
    assert len(result) == 2

    # Verify shares persisted in database
    async with default_session_factory() as session:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ShareDocument)
            .options(selectinload(ShareDocument.user))
            .where(ShareDocument.document_id == document_id)
        )
        db_result = await session.execute(stmt)
        db_shares = list(db_result.scalars().all())

        assert len(db_shares) == 2
        assert all(share.document_id == document_id for share in db_shares)
        shared_user_ids = [share.user_id for share in db_shares]
        assert user1_id in shared_user_ids
        assert user2_id in shared_user_ids
        # Verify dates
        assert all(
            share.start_date.strftime("%Y-%m-%d") == "2024-01-01" for share in db_shares
        )
        assert all(
            share.end_date.strftime("%Y-%m-%d") == "2024-12-31" for share in db_shares
        )


@pytest.mark.asyncio
async def test_share_document_without_dates_persists(document_service, test_data):
    """Test that sharing document without dates persists correctly."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User
    from core.models import ShareDocument

    # Create user to share with
    async with default_session_factory() as session:
        user = User(
            first_name="Share",
            last_name="User",
            username="share_user_no_dates_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    # Create a document
    document_data = DocumentCreate(
        name="Document Share Without Dates Integration",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("share_no_dates.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Share without dates
    share_data = ShareDocumentCreate(user_ids=[user_id])

    result = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=test_data["user_id"],
    )

    # Verify share created
    assert not isinstance(result, Error)
    assert len(result) == 1
    assert result[0].start_date is None
    assert result[0].end_date is None

    # Verify in database
    async with default_session_factory() as session:
        stmt = select(ShareDocument).where(ShareDocument.document_id == document_id)
        db_result = await session.execute(stmt)
        db_share = db_result.scalar_one_or_none()

        assert db_share is not None
        assert db_share.start_date is None
        assert db_share.end_date is None


@pytest.mark.asyncio
async def test_share_document_creates_document_history(document_service, test_data):
    """Test that sharing document creates document history entry."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    # Create user to share with
    async with default_session_factory() as session:
        user = User(
            first_name="Share",
            last_name="User",
            username="share_user_history_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    # Create a document
    document_data = DocumentCreate(
        name="Document Share History Integration",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("share_history.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Share the document
    share_data = ShareDocumentCreate(user_ids=[user_id])

    result = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(result, Error)

    # Verify document history entry created in database
    async with default_session_factory() as session:
        stmt = (
            select(DocumentHistory)
            .where(DocumentHistory.document_id == document_id)
            .where(DocumentHistory.action == "Share Document")
            .order_by(DocumentHistory.created_at.desc())
        )
        db_result = await session.execute(stmt)
        history_entry = db_result.scalars().first()

        assert history_entry is not None
        assert "shared with users" in history_entry.description.lower()
        assert history_entry.created_by == test_data["user_id"]


@pytest.mark.asyncio
async def test_share_document_invalid_date_range(document_service, test_data):
    """Test that sharing with invalid date range returns error."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    # Create user to share with
    async with default_session_factory() as session:
        user = User(
            first_name="Share",
            last_name="User",
            username="share_user_invalid_dates_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    # Create a document
    document_data = DocumentCreate(
        name="Document Invalid Date Range Integration",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("invalid_dates.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Try to share with end date before start date
    share_data = ShareDocumentCreate(
        user_ids=[user_id],
        start_date="2024-12-31",
        end_date="2024-01-01",
    )

    result = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=test_data["user_id"],
    )

    # Verify error
    assert isinstance(result, Error)
    assert result.code == 400
    assert "start date must be before end date" in result.detail.lower()


@pytest.mark.asyncio
async def test_share_document_not_found(document_service, test_data):
    """Test sharing non-existent document returns error."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    # Create user to share with
    async with default_session_factory() as session:
        user = User(
            first_name="Share",
            last_name="User",
            username="share_user_not_found_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    non_existent_id = uuid4()
    share_data = ShareDocumentCreate(user_ids=[user_id])

    result = await document_service.share_document(
        document_id=non_existent_id,
        share_data=share_data,
        current_user_id=test_data["user_id"],
    )

    assert isinstance(result, Error)
    assert result.code == 404
    assert "document not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_share_document_user_not_found(document_service, test_data):
    """Test sharing document with non-existent user returns error."""
    # Create a document
    document_data = DocumentCreate(
        name="Document User Not Found Integration",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("user_not_found.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Try to share with non-existent user

    non_existent_user = uuid4()
    share_data = ShareDocumentCreate(user_ids=[non_existent_user])

    result = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=test_data["user_id"],
    )

    assert isinstance(result, Error)
    assert result.code == 404
    assert "user not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_share_document_skip_duplicate_in_database(document_service, test_data):
    """Test that duplicate shares are skipped and not persisted."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User
    from core.models import ShareDocument

    # Create user to share with
    async with default_session_factory() as session:
        user = User(
            first_name="Share",
            last_name="User",
            username="share_user_duplicate_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    # Create a document
    document_data = DocumentCreate(
        name="Document Duplicate Share Integration",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("duplicate_share.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Share the document first time
    share_data = ShareDocumentCreate(user_ids=[user_id])
    result1 = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(result1, Error)
    assert len(result1) == 1

    # Verify one share in database
    async with default_session_factory() as session:
        stmt = select(ShareDocument).where(ShareDocument.document_id == document_id)
        db_result = await session.execute(stmt)
        db_shares = list(db_result.scalars().all())
        assert len(db_shares) == 1

    # Try to share with same user again
    result2 = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=test_data["user_id"],
    )

    # Should skip duplicate and return empty list
    assert not isinstance(result2, Error)
    assert len(result2) == 0

    # Verify still only one share in database
    async with default_session_factory() as session:
        stmt = select(ShareDocument).where(ShareDocument.document_id == document_id)
        db_result = await session.execute(stmt)
        db_shares = list(db_result.scalars().all())
        assert len(db_shares) == 1


@pytest.mark.asyncio
async def test_get_shared_users_retrieves_from_database(document_service, test_data):
    """Test that getting shared users retrieves data from database."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User
    from core.models import ShareDocument

    # Create users to share with
    async with default_session_factory() as session:
        user1 = User(
            first_name="Get",
            last_name="User1",
            username="get_share_user1_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        user2 = User(
            first_name="Get",
            last_name="User2",
            username="get_share_user2_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add_all([user1, user2])
        await session.commit()
        await session.refresh(user1)
        await session.refresh(user2)
        user1_id = user1.id
        user2_id = user2.id

    # Create a document
    document_data = DocumentCreate(
        name="Document Get Shared Users Integration",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("get_shared_users.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Share the document
    share_data = ShareDocumentCreate(user_ids=[user1_id, user2_id])
    await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=test_data["user_id"],
    )

    # Get shared users
    result = await document_service.get_shared_users(document_id=document_id)

    # Verify
    assert not isinstance(result, Error)
    assert len(result) == 2
    assert all(share.document_id == document_id for share in result)
    shared_user_ids = [share.user_id for share in result]
    assert user1_id in shared_user_ids
    assert user2_id in shared_user_ids

    # Verify all shares have user relationship populated
    assert all(share.user is not None for share in result)

    # Verify shares exist in database
    async with default_session_factory() as session:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ShareDocument)
            .options(selectinload(ShareDocument.user))
            .where(ShareDocument.document_id == document_id)
        )
        db_result = await session.execute(stmt)
        db_shares = list(db_result.scalars().all())

        assert len(db_shares) == 2
        assert all(share.user is not None for share in db_shares)


@pytest.mark.asyncio
async def test_get_shared_users_document_not_found(document_service):
    """Test getting shared users for non-existent document returns error."""
    non_existent_id = uuid4()

    result = await document_service.get_shared_users(document_id=non_existent_id)

    assert isinstance(result, Error)
    assert result.code == 404
    assert "document not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_shared_users_empty(document_service, test_data):
    """Test getting shared users when none exist returns empty list."""
    # Create a document without sharing
    document_data = DocumentCreate(
        name="Document No Shares Integration",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("no_shares.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Get shared users (should be empty)
    result = await document_service.get_shared_users(document_id=document_id)

    # Should return empty list
    assert not isinstance(result, Error)
    assert isinstance(result, list)
    assert len(result) == 0

    # Verify no shares in database
    async with default_session_factory() as session:
        from core.models import ShareDocument

        stmt = select(ShareDocument).where(ShareDocument.document_id == document_id)
        db_result = await session.execute(stmt)
        db_shares = list(db_result.scalars().all())
        assert len(db_shares) == 0


@pytest.mark.asyncio
async def test_get_shared_users_ordered_by_date_descending(document_service, test_data):
    """Test that shared users are ordered by created_at descending."""
    import asyncio

    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    # Create users to share with
    async with default_session_factory() as session:
        user1 = User(
            first_name="Order",
            last_name="User1",
            username="order_share_user1_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        user2 = User(
            first_name="Order",
            last_name="User2",
            username="order_share_user2_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        user3 = User(
            first_name="Order",
            last_name="User3",
            username="order_share_user3_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add_all([user1, user2, user3])
        await session.commit()
        await session.refresh(user1)
        await session.refresh(user2)
        await session.refresh(user3)
        user1_id = user1.id
        user2_id = user2.id
        user3_id = user3.id

    # Create a document
    document_data = DocumentCreate(
        name="Document Share Ordering Integration",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("share_ordering.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Share with users sequentially with delays
    await asyncio.sleep(0.1)
    share_data1 = ShareDocumentCreate(user_ids=[user1_id])
    await document_service.share_document(
        document_id=document_id,
        share_data=share_data1,
        current_user_id=test_data["user_id"],
    )

    await asyncio.sleep(0.1)
    share_data2 = ShareDocumentCreate(user_ids=[user2_id])
    await document_service.share_document(
        document_id=document_id,
        share_data=share_data2,
        current_user_id=test_data["user_id"],
    )

    await asyncio.sleep(0.1)
    share_data3 = ShareDocumentCreate(user_ids=[user3_id])
    await document_service.share_document(
        document_id=document_id,
        share_data=share_data3,
        current_user_id=test_data["user_id"],
    )

    # Get shared users
    result = await document_service.get_shared_users(document_id=document_id)

    # Verify shares are ordered newest first
    assert not isinstance(result, Error)
    assert len(result) == 3

    # Verify timestamps are in descending order (newest first)
    for i in range(len(result) - 1):
        assert result[i].created_at >= result[i + 1].created_at

    # Verify all users are present in the results
    result_user_ids = [share.user_id for share in result]
    assert user1_id in result_user_ids
    assert user2_id in result_user_ids
    assert user3_id in result_user_ids


@pytest.mark.asyncio
async def test_delete_share_document_removes_from_database(document_service, test_data):
    """Test that deleting a share document removes it from the database."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User
    from core.models import ShareDocument

    # Create user to share with
    async with default_session_factory() as session:
        user = User(
            first_name="Share",
            last_name="User",
            username="share_user_delete_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    # Create a document
    document_data = DocumentCreate(
        name="Document to Delete Share Integration",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("delete_share_integration.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Share the document
    share_data = ShareDocumentCreate(user_ids=[user_id])
    share_result = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(share_result, Error)
    assert len(share_result) == 1
    share_id = share_result[0].id

    # Verify share exists in database
    async with default_session_factory() as session:
        stmt = select(ShareDocument).where(ShareDocument.id == share_id)
        db_result = await session.execute(stmt)
        db_share = db_result.scalar_one_or_none()
        assert db_share is not None

    # Delete the share
    result = await document_service.delete_share_document(
        document_id=document_id,
        share_id=share_id,
        current_user_id=test_data["user_id"],
    )

    # Verify deletion was successful
    assert not isinstance(result, Error)
    assert result.detail == "Assigned document successfully removed!"

    # Verify share was removed from database
    async with default_session_factory() as session:
        stmt = select(ShareDocument).where(ShareDocument.id == share_id)
        db_result = await session.execute(stmt)
        db_share = db_result.scalar_one_or_none()
        assert db_share is None


@pytest.mark.asyncio
async def test_delete_share_document_creates_history(document_service, test_data):
    """Test that deleting a share document creates document history entry."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    # Create user to share with
    async with default_session_factory() as session:
        user = User(
            first_name="Share",
            last_name="User",
            username="share_user_history_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    # Create a document
    document_data = DocumentCreate(
        name="Document History Delete Share",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("history_delete_share.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Share the document
    share_data = ShareDocumentCreate(user_ids=[user_id])
    share_result = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(share_result, Error)
    share_id = share_result[0].id

    # Delete the share
    result = await document_service.delete_share_document(
        document_id=document_id,
        share_id=share_id,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(result, Error)

    # Verify document history was created in database
    async with default_session_factory() as session:
        stmt = (
            select(DocumentHistory)
            .where(DocumentHistory.document_id == document_id)
            .where(DocumentHistory.action == "Share Document Delete")
        )
        db_result = await session.execute(stmt)
        history_entries = list(db_result.scalars().all())

        assert len(history_entries) > 0
        assert "deleted" in history_entries[-1].description.lower()
        assert "share user" in history_entries[-1].description.lower()


@pytest.mark.asyncio
async def test_delete_share_document_not_found(document_service, test_data):
    """Test that deleting non-existent share returns error."""
    # Create a document
    document_data = DocumentCreate(
        name="Document Delete Share Not Found",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file = create_upload_file("delete_share_not_found.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, test_data["user_id"]
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Try to delete non-existent share
    non_existent_share_id = uuid4()
    result = await document_service.delete_share_document(
        document_id=document_id,
        share_id=non_existent_share_id,
        current_user_id=test_data["user_id"],
    )

    assert isinstance(result, Error)
    assert result.code == 404
    assert "share not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_delete_share_document_wrong_document(document_service, test_data):
    """Test that deleting share with mismatched document ID returns error."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    # Create user to share with
    async with default_session_factory() as session:
        user = User(
            first_name="Share",
            last_name="User",
            username="share_user_wrong_doc_integration",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    # Create first document
    document_data1 = DocumentCreate(
        name="Document 1 Wrong Doc",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file1 = create_upload_file("wrong_doc1.pdf")
    created_document1 = await document_service.create_document(
        document_data1, upload_file1, test_data["user_id"]
    )

    assert not isinstance(created_document1, Error)
    document_id1 = created_document1.id

    # Create second document
    document_data2 = DocumentCreate(
        name="Document 2 Wrong Doc",
        category_id=test_data["category_id"],
        subcategory_id=test_data["subcategory_id"],
        stage_id=test_data["stage_id"],
        assigned_to=test_data["user_id"],
    )

    upload_file2 = create_upload_file("wrong_doc2.pdf")
    created_document2 = await document_service.create_document(
        document_data2, upload_file2, test_data["user_id"]
    )

    assert not isinstance(created_document2, Error)
    document_id2 = created_document2.id

    # Share document 1
    share_data = ShareDocumentCreate(user_ids=[user_id])
    share_result = await document_service.share_document(
        document_id=document_id1,
        share_data=share_data,
        current_user_id=test_data["user_id"],
    )

    assert not isinstance(share_result, Error)
    share_id = share_result[0].id

    # Try to delete share using wrong document ID
    result = await document_service.delete_share_document(
        document_id=document_id2,  # Wrong document ID
        share_id=share_id,
        current_user_id=test_data["user_id"],
    )

    assert isinstance(result, Error)
    assert result.code == 400
    assert "does not belong to this document" in result.detail.lower()


# ==================== Reminder Integration Tests ====================
