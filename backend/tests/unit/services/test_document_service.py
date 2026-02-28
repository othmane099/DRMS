import os
import sys
from datetime import datetime
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import UploadFile
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from configuration.models import Category, Stage, Subcategory
from core.documents.schemas import (
    DocumentCreate,
    ShareDocumentCreate,
    DocumentFilterParams,
)
from core.documents.service import DocumentServiceImpl
from core.models import Document
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
@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_create_document_success(document_service, uow):
    """Test creating a new document successfully."""
    from configuration.models import Tag

    # Create test tags
    tag1_id = uuid4()
    tag2_id = uuid4()
    uow.tag_repository.tags[tag1_id] = Tag(id=tag1_id, title="tag1")
    uow.tag_repository.tags[tag2_id] = Tag(id=tag2_id, title="tag2")

    document_data = DocumentCreate(
        name="Test Document",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        description="Test description",
        tag_ids=[tag1_id, tag2_id],
    )

    upload_file = create_upload_file("test.pdf")
    result = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert not isinstance(result, Error)
    assert result.name == "Test Document"
    assert result.description == "Test description"
    assert len(result.tags) == 2
    assert result.tags[0].id == tag1_id
    assert result.tags[1].id == tag2_id
    assert result.category_id == uow.test_category_id
    assert result.subcategory_id == uow.test_subcategory_id
    assert result.stage_id == uow.test_stage_id
    assert result.assigned_to == uow.test_user_id
    assert result.created_by == uow.test_user_id


@pytest.mark.asyncio
async def test_create_document_duplicate_name(document_service, uow):
    """Test creating a document with duplicate name fails."""
    document_data = DocumentCreate(
        name="Duplicate Document",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
    )

    upload_file1 = create_upload_file("test1.pdf")
    await document_service.create_document(
        document_data, upload_file1, uow.test_user_id
    )

    upload_file2 = create_upload_file("test2.pdf")
    result = await document_service.create_document(
        document_data, upload_file2, uow.test_user_id
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "name already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_create_document_invalid_category(document_service, uow):
    """Test creating a document with invalid category fails."""
    document_data = DocumentCreate(
        name="Test Document",
        category_id=uuid4(),  # Non-existent category
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
    )

    upload_file = create_upload_file("test.pdf")
    result = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "category not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_create_document_invalid_subcategory(document_service, uow):
    """Test creating a document with invalid subcategory fails."""
    document_data = DocumentCreate(
        name="Test Document",
        category_id=uow.test_category_id,
        subcategory_id=uuid4(),  # Non-existent subcategory
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
    )

    upload_file = create_upload_file("test.pdf")
    result = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "subcategory not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_create_document_invalid_stage(document_service, uow):
    """Test creating a document with invalid stage fails."""
    document_data = DocumentCreate(
        name="Test Document",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uuid4(),  # Non-existent stage
        assigned_to=uow.test_user_id,
    )

    upload_file = create_upload_file("test.pdf")
    result = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "stage not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_create_document_invalid_assigned_user(document_service, uow):
    """Test creating a document with invalid assigned user fails."""
    document_data = DocumentCreate(
        name="Test Document",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uuid4(),  # Non-existent user
    )

    upload_file = create_upload_file("test.pdf")
    result = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "assigned user not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_all_documents_paginated_success(document_service, uow):
    """Test retrieving documents with pagination."""
    # Create test documents
    for i in range(15):
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name=f"Document {i}",
            category_id=uow.test_category_id,
            subcategory_id=uow.test_subcategory_id,
            stage_id=uow.test_stage_id,
            assigned_to=uow.test_user_id,
            archive=False,
            created_by=uow.test_user_id,
            created_at=datetime.now(),
        )
        # Populate relationships for DocumentResponse validation
        doc.category = uow.category_repository.categories[uow.test_category_id]
        doc.subcategory = uow.subcategory_repository.subcategories[
            uow.test_subcategory_id
        ]
        doc.stage = uow.stage_repository.stages[uow.test_stage_id]
        doc.creator = uow.user_repository.users[uow.test_user_id]
        doc.assigned_user = uow.user_repository.users[uow.test_user_id]
        doc.tags = []
        uow.document_repository.documents[doc_id] = doc

    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(**{"page": 1, "page_size": 10}),
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 10
    assert result.total_rows == 15
    assert result.total_pages == 2
    assert result.current_page == 1
    assert result.has_next is True
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_get_all_documents_paginated_with_filters(document_service, uow):
    """Test retrieving documents with filters."""
    # Create documents with different categories
    category_id_2 = uuid4()
    uow.category_repository.categories[category_id_2] = Category(
        id=category_id_2, title="Category 2"
    )

    for i in range(5):
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name=f"Doc Cat 1 - {i}",
            category_id=uow.test_category_id,
            subcategory_id=uow.test_subcategory_id,
            stage_id=uow.test_stage_id,
            assigned_to=uow.test_user_id,
            archive=False,
            created_by=uow.test_user_id,
            created_at=datetime.now(),
        )
        # Populate relationships for DocumentResponse validation
        doc.category = uow.category_repository.categories[uow.test_category_id]
        doc.subcategory = uow.subcategory_repository.subcategories[
            uow.test_subcategory_id
        ]
        doc.stage = uow.stage_repository.stages[uow.test_stage_id]
        doc.creator = uow.user_repository.users[uow.test_user_id]
        doc.assigned_user = uow.user_repository.users[uow.test_user_id]
        doc.tags = []
        uow.document_repository.documents[doc_id] = doc

    for i in range(3):
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name=f"Doc Cat 2 - {i}",
            category_id=category_id_2,
            subcategory_id=uow.test_subcategory_id,
            stage_id=uow.test_stage_id,
            assigned_to=uow.test_user_id,
            archive=False,
            created_by=uow.test_user_id,
            created_at=datetime.now(),
        )
        # Populate relationships for DocumentResponse validation
        doc.category = uow.category_repository.categories[category_id_2]
        doc.subcategory = uow.subcategory_repository.subcategories[
            uow.test_subcategory_id
        ]
        doc.stage = uow.stage_repository.stages[uow.test_stage_id]
        doc.creator = uow.user_repository.users[uow.test_user_id]
        doc.assigned_user = uow.user_repository.users[uow.test_user_id]
        doc.tags = []
        uow.document_repository.documents[doc_id] = doc

    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(
            **{"page": 1, "page_size": 10, "category_id": uow.test_category_id}
        )
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 5
    assert result.total_rows == 5


@pytest.mark.asyncio
async def test_get_all_documents_empty(document_service):
    """Test retrieving documents when none exist."""
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(**{"page": 1, "page_size": 10})
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 0
    assert result.total_rows == 0
    assert result.total_pages == 0


@pytest.mark.asyncio
async def test_get_documents_paginated_with_user_filter_created_by(
    document_service, uow
):
    """Test retrieving documents filtered by user (documents created by user)."""
    from auth.models import User

    # Create additional users
    user1_id = uuid4()
    user2_id = uuid4()
    uow.user_repository.users[user1_id] = User(
        id=user1_id,
        first_name="User",
        last_name="One",
        username="user1",
        password="hashed",
        is_active=True,
    )
    uow.user_repository.users[user2_id] = User(
        id=user2_id,
        first_name="User",
        last_name="Two",
        username="user2",
        password="hashed",
        is_active=True,
    )

    # Create documents for user1 (creator)
    for i in range(3):
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name=f"User1 Created Doc {i}",
            category_id=uow.test_category_id,
            subcategory_id=uow.test_subcategory_id,
            stage_id=uow.test_stage_id,
            assigned_to=uow.test_user_id,
            created_by=user1_id,
            archive=False,
            created_at=datetime.now(),
        )
        doc.category = uow.category_repository.categories[uow.test_category_id]
        doc.subcategory = uow.subcategory_repository.subcategories[
            uow.test_subcategory_id
        ]
        doc.stage = uow.stage_repository.stages[uow.test_stage_id]
        doc.creator = uow.user_repository.users[user1_id]
        doc.assigned_user = uow.user_repository.users[uow.test_user_id]
        doc.tags = []
        uow.document_repository.documents[doc_id] = doc

    # Create documents for user2 (creator)
    for i in range(2):
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name=f"User2 Created Doc {i}",
            category_id=uow.test_category_id,
            subcategory_id=uow.test_subcategory_id,
            stage_id=uow.test_stage_id,
            assigned_to=uow.test_user_id,
            created_by=user2_id,
            archive=False,
            created_at=datetime.now(),
        )
        doc.category = uow.category_repository.categories[uow.test_category_id]
        doc.subcategory = uow.subcategory_repository.subcategories[
            uow.test_subcategory_id
        ]
        doc.stage = uow.stage_repository.stages[uow.test_stage_id]
        doc.creator = uow.user_repository.users[user2_id]
        doc.assigned_user = uow.user_repository.users[uow.test_user_id]
        doc.tags = []
        uow.document_repository.documents[doc_id] = doc

    # Get documents for user1
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(
            **{
                "page": 1,
                "page_size": 10,
            }
        ),
        user_id=user1_id,
    )

    assert not isinstance(result, Error)
    assert result.total_rows == 3
    assert all(doc.created_by == user1_id for doc in result.data)


@pytest.mark.asyncio
async def test_get_documents_paginated_with_user_filter_assigned_to(
    document_service, uow
):
    """Test retrieving documents filtered by user (documents assigned to user)."""
    from auth.models import User

    # Create additional users
    user1_id = uuid4()
    user2_id = uuid4()
    uow.user_repository.users[user1_id] = User(
        id=user1_id,
        first_name="User",
        last_name="One",
        username="user1",
        password="hashed",
        is_active=True,
    )
    uow.user_repository.users[user2_id] = User(
        id=user2_id,
        first_name="User",
        last_name="Two",
        username="user2",
        password="hashed",
        is_active=True,
    )

    # Create documents assigned to user1
    for i in range(3):
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name=f"Assigned to User1 Doc {i}",
            category_id=uow.test_category_id,
            subcategory_id=uow.test_subcategory_id,
            stage_id=uow.test_stage_id,
            assigned_to=user1_id,
            created_by=uow.test_user_id,
            archive=False,
            created_at=datetime.now(),
        )
        doc.category = uow.category_repository.categories[uow.test_category_id]
        doc.subcategory = uow.subcategory_repository.subcategories[
            uow.test_subcategory_id
        ]
        doc.stage = uow.stage_repository.stages[uow.test_stage_id]
        doc.creator = uow.user_repository.users[uow.test_user_id]
        doc.assigned_user = uow.user_repository.users[user1_id]
        doc.tags = []
        uow.document_repository.documents[doc_id] = doc

    # Create documents assigned to user2
    for i in range(2):
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name=f"Assigned to User2 Doc {i}",
            category_id=uow.test_category_id,
            subcategory_id=uow.test_subcategory_id,
            stage_id=uow.test_stage_id,
            assigned_to=user2_id,
            created_by=uow.test_user_id,
            archive=False,
            created_at=datetime.now(),
        )
        doc.category = uow.category_repository.categories[uow.test_category_id]
        doc.subcategory = uow.subcategory_repository.subcategories[
            uow.test_subcategory_id
        ]
        doc.stage = uow.stage_repository.stages[uow.test_stage_id]
        doc.creator = uow.user_repository.users[uow.test_user_id]
        doc.assigned_user = uow.user_repository.users[user2_id]
        doc.tags = []
        uow.document_repository.documents[doc_id] = doc

    # Get documents for user1
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(
            **{
                "page": 1,
                "page_size": 10,
            }
        ),
        user_id=user1_id,
    )

    assert not isinstance(result, Error)
    assert result.total_rows == 3
    assert all(doc.assigned_to == user1_id for doc in result.data)


@pytest.mark.asyncio
async def test_get_documents_paginated_with_user_filter_shared_with_user(
    document_service, uow
):
    """Test retrieving documents filtered by user (documents shared with user)."""
    from datetime import date, timedelta

    from auth.models import User
    from core.models import ShareDocument

    # Create additional user
    user1_id = uuid4()
    uow.user_repository.users[user1_id] = User(
        id=user1_id,
        first_name="Shared",
        last_name="User",
        username="shareduser",
        password="hashed",
        is_active=True,
    )

    # Create documents owned by test user
    doc_ids = []
    for i in range(3):
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name=f"Shared Doc {i}",
            category_id=uow.test_category_id,
            subcategory_id=uow.test_subcategory_id,
            stage_id=uow.test_stage_id,
            assigned_to=uow.test_user_id,
            created_by=uow.test_user_id,
            archive=False,
            created_at=datetime.now(),
        )
        doc.category = uow.category_repository.categories[uow.test_category_id]
        doc.subcategory = uow.subcategory_repository.subcategories[
            uow.test_subcategory_id
        ]
        doc.stage = uow.stage_repository.stages[uow.test_stage_id]
        doc.creator = uow.user_repository.users[uow.test_user_id]
        doc.assigned_user = uow.user_repository.users[uow.test_user_id]
        doc.tags = []
        uow.document_repository.documents[doc_id] = doc
        doc_ids.append(doc_id)

    # Share documents with user1 (with valid date range)
    today = date.today()
    for doc_id in doc_ids:
        share_id = uuid4()
        share = ShareDocument(
            id=share_id,
            document_id=doc_id,
            user_id=user1_id,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=30),
            created_at=datetime.now(),
        )
        share.user = uow.user_repository.users[user1_id]
        uow.document_repository.shares[share_id] = share

    # Get documents for user1
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(
            **{
                "page": 1,
                "page_size": 10,
            }
        ),
        user_id=user1_id,
    )

    assert not isinstance(result, Error)
    assert result.total_rows == 3
    # User1 should see the shared documents
    returned_doc_ids = [doc.id for doc in result.data]
    assert all(doc_id in returned_doc_ids for doc_id in doc_ids)


@pytest.mark.asyncio
async def test_get_documents_paginated_shared_not_yet_started(document_service, uow):
    """Test that shared documents with future start_date are not accessible."""
    from datetime import date, timedelta

    from auth.models import User
    from core.models import ShareDocument

    # Create additional user
    user1_id = uuid4()
    uow.user_repository.users[user1_id] = User(
        id=user1_id,
        first_name="Future",
        last_name="User",
        username="futureuser",
        password="hashed",
        is_active=True,
    )

    # Create a document owned by test user
    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        name="Future Shared Doc",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        created_by=uow.test_user_id,
        archive=False,
        created_at=datetime.now(),
    )
    doc.category = uow.category_repository.categories[uow.test_category_id]
    doc.subcategory = uow.subcategory_repository.subcategories[uow.test_subcategory_id]
    doc.stage = uow.stage_repository.stages[uow.test_stage_id]
    doc.creator = uow.user_repository.users[uow.test_user_id]
    doc.assigned_user = uow.user_repository.users[uow.test_user_id]
    doc.tags = []
    uow.document_repository.documents[doc_id] = doc

    # Share document with user1 (with future start_date)
    today = date.today()
    share_id = uuid4()
    share = ShareDocument(
        id=share_id,
        document_id=doc_id,
        user_id=user1_id,
        start_date=today + timedelta(days=7),  # Starts in the future
        end_date=today + timedelta(days=30),
        created_at=datetime.now(),
    )
    share.user = uow.user_repository.users[user1_id]
    uow.document_repository.shares[share_id] = share

    # Get documents for user1
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(**{"page": 1, "page_size": 10}),
        user_id=user1_id,
    )

    assert not isinstance(result, Error)
    # User1 should NOT see the document (share hasn't started yet)
    assert result.total_rows == 0
    assert len(result.data) == 0


@pytest.mark.asyncio
async def test_get_documents_paginated_shared_expired(document_service, uow):
    """Test that shared documents with past end_date are not accessible."""
    from datetime import date, timedelta

    from auth.models import User
    from core.models import ShareDocument

    # Create additional user
    user1_id = uuid4()
    uow.user_repository.users[user1_id] = User(
        id=user1_id,
        first_name="Expired",
        last_name="User",
        username="expireduser",
        password="hashed",
        is_active=True,
    )

    # Create a document owned by test user
    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        name="Expired Shared Doc",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        created_by=uow.test_user_id,
        archive=False,
        created_at=datetime.now(),
    )
    doc.category = uow.category_repository.categories[uow.test_category_id]
    doc.subcategory = uow.subcategory_repository.subcategories[uow.test_subcategory_id]
    doc.stage = uow.stage_repository.stages[uow.test_stage_id]
    doc.creator = uow.user_repository.users[uow.test_user_id]
    doc.assigned_user = uow.user_repository.users[uow.test_user_id]
    doc.tags = []
    uow.document_repository.documents[doc_id] = doc

    # Share document with user1 (with past end_date)
    today = date.today()
    share_id = uuid4()
    share = ShareDocument(
        id=share_id,
        document_id=doc_id,
        user_id=user1_id,
        start_date=today - timedelta(days=30),
        end_date=today - timedelta(days=1),  # Expired yesterday
        created_at=datetime.now(),
    )
    share.user = uow.user_repository.users[user1_id]
    uow.document_repository.shares[share_id] = share

    # Get documents for user1
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(**{"page": 1, "page_size": 10}), user_id=user1_id
    )

    assert not isinstance(result, Error)
    # User1 should NOT see the document (share has expired)
    assert result.total_rows == 0
    assert len(result.data) == 0


@pytest.mark.asyncio
async def test_get_documents_paginated_shared_without_date_constraints(
    document_service, uow
):
    """Test shared documents without start_date and end_date are always accessible."""
    from auth.models import User
    from core.models import ShareDocument

    # Create additional user
    user1_id = uuid4()
    uow.user_repository.users[user1_id] = User(
        id=user1_id,
        first_name="Permanent",
        last_name="User",
        username="permuser",
        password="hashed",
        is_active=True,
    )

    # Create a document owned by test user
    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        name="Permanent Shared Doc",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        created_by=uow.test_user_id,
        archive=False,
        created_at=datetime.now(),
    )
    doc.category = uow.category_repository.categories[uow.test_category_id]
    doc.subcategory = uow.subcategory_repository.subcategories[uow.test_subcategory_id]
    doc.stage = uow.stage_repository.stages[uow.test_stage_id]
    doc.creator = uow.user_repository.users[uow.test_user_id]
    doc.assigned_user = uow.user_repository.users[uow.test_user_id]
    doc.tags = []
    uow.document_repository.documents[doc_id] = doc

    # Share document with user1 (without date constraints - permanent access)
    share_id = uuid4()
    share = ShareDocument(
        id=share_id,
        document_id=doc_id,
        user_id=user1_id,
        start_date=None,
        end_date=None,
        created_at=datetime.now(),
    )
    share.user = uow.user_repository.users[user1_id]
    uow.document_repository.shares[share_id] = share

    # Get documents for user1
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(
            **{
                "page": 1,
                "page_size": 10,
            }
        ),
        user_id=user1_id,
    )

    assert not isinstance(result, Error)
    # User1 should see the document (permanent access)
    assert result.total_rows == 1
    assert result.data[0].id == doc_id


@pytest.mark.asyncio
async def test_get_documents_paginated_user_multiple_access_types(
    document_service, uow
):
    """Test user sees documents where they have multiple access types (creator, assigned, shared)."""
    from datetime import date, timedelta

    from auth.models import User
    from core.models import ShareDocument

    # Create additional user
    user1_id = uuid4()
    user2_id = uuid4()
    uow.user_repository.users[user1_id] = User(
        id=user1_id,
        first_name="Multi",
        last_name="Access",
        username="multiaccess",
        password="hashed",
        is_active=True,
    )
    uow.user_repository.users[user2_id] = User(
        id=user2_id,
        first_name="Other",
        last_name="User",
        username="otheruser",
        password="hashed",
        is_active=True,
    )

    # Create document where user1 is creator
    doc1_id = uuid4()
    doc1 = Document(
        id=doc1_id,
        name="Doc Created By User1",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=user2_id,
        created_by=user1_id,
        archive=False,
        created_at=datetime.now(),
    )
    doc1.category = uow.category_repository.categories[uow.test_category_id]
    doc1.subcategory = uow.subcategory_repository.subcategories[uow.test_subcategory_id]
    doc1.stage = uow.stage_repository.stages[uow.test_stage_id]
    doc1.creator = uow.user_repository.users[user1_id]
    doc1.assigned_user = uow.user_repository.users[user2_id]
    doc1.tags = []
    uow.document_repository.documents[doc1_id] = doc1

    # Create document where user1 is assigned
    doc2_id = uuid4()
    doc2 = Document(
        id=doc2_id,
        name="Doc Assigned To User1",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=user1_id,
        created_by=user2_id,
        archive=False,
        created_at=datetime.now(),
    )
    doc2.category = uow.category_repository.categories[uow.test_category_id]
    doc2.subcategory = uow.subcategory_repository.subcategories[uow.test_subcategory_id]
    doc2.stage = uow.stage_repository.stages[uow.test_stage_id]
    doc2.creator = uow.user_repository.users[user2_id]
    doc2.assigned_user = uow.user_repository.users[user1_id]
    doc2.tags = []
    uow.document_repository.documents[doc2_id] = doc2

    # Create document shared with user1
    doc3_id = uuid4()
    doc3 = Document(
        id=doc3_id,
        name="Doc Shared With User1",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=user2_id,
        created_by=user2_id,
        archive=False,
        created_at=datetime.now(),
    )
    doc3.category = uow.category_repository.categories[uow.test_category_id]
    doc3.subcategory = uow.subcategory_repository.subcategories[uow.test_subcategory_id]
    doc3.stage = uow.stage_repository.stages[uow.test_stage_id]
    doc3.creator = uow.user_repository.users[user2_id]
    doc3.assigned_user = uow.user_repository.users[user2_id]
    doc3.tags = []
    uow.document_repository.documents[doc3_id] = doc3

    # Share doc3 with user1
    today = date.today()
    share_id = uuid4()
    share = ShareDocument(
        id=share_id,
        document_id=doc3_id,
        user_id=user1_id,
        start_date=today - timedelta(days=1),
        end_date=today + timedelta(days=30),
        created_at=datetime.now(),
    )
    share.user = uow.user_repository.users[user1_id]
    uow.document_repository.shares[share_id] = share

    # Create document where user1 has NO access
    doc4_id = uuid4()
    doc4 = Document(
        id=doc4_id,
        name="Doc No Access For User1",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=user2_id,
        created_by=user2_id,
        archive=False,
        created_at=datetime.now(),
    )
    doc4.category = uow.category_repository.categories[uow.test_category_id]
    doc4.subcategory = uow.subcategory_repository.subcategories[uow.test_subcategory_id]
    doc4.stage = uow.stage_repository.stages[uow.test_stage_id]
    doc4.creator = uow.user_repository.users[user2_id]
    doc4.assigned_user = uow.user_repository.users[user2_id]
    doc4.tags = []
    uow.document_repository.documents[doc4_id] = doc4

    # Get documents for user1
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(**{"page": 1, "page_size": 10}),
        user_id=user1_id,
    )

    assert not isinstance(result, Error)
    # User1 should see 3 documents (created, assigned, and shared)
    assert result.total_rows == 3
    returned_doc_ids = [doc.id for doc in result.data]
    assert doc1_id in returned_doc_ids  # Created by user1
    assert doc2_id in returned_doc_ids  # Assigned to user1
    assert doc3_id in returned_doc_ids  # Shared with user1
    assert doc4_id not in returned_doc_ids  # No access


@pytest.mark.asyncio
async def test_get_documents_paginated_user_filter_with_category_filter(
    document_service, uow
):
    """Test combining user filter with category filter."""
    from auth.models import User

    # Create additional user
    user1_id = uuid4()
    uow.user_repository.users[user1_id] = User(
        id=user1_id,
        first_name="Filter",
        last_name="User",
        username="filteruser",
        password="hashed",
        is_active=True,
    )

    # Create another category
    category2_id = uuid4()
    uow.category_repository.categories[category2_id] = Category(
        id=category2_id, title="Category 2"
    )

    # Create documents in category 1 for user1
    for i in range(3):
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name=f"User1 Cat1 Doc {i}",
            category_id=uow.test_category_id,
            subcategory_id=uow.test_subcategory_id,
            stage_id=uow.test_stage_id,
            assigned_to=user1_id,
            created_by=uow.test_user_id,
            archive=False,
            created_at=datetime.now(),
        )
        doc.category = uow.category_repository.categories[uow.test_category_id]
        doc.subcategory = uow.subcategory_repository.subcategories[
            uow.test_subcategory_id
        ]
        doc.stage = uow.stage_repository.stages[uow.test_stage_id]
        doc.creator = uow.user_repository.users[uow.test_user_id]
        doc.assigned_user = uow.user_repository.users[user1_id]
        doc.tags = []
        uow.document_repository.documents[doc_id] = doc

    # Create documents in category 2 for user1
    for i in range(2):
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name=f"User1 Cat2 Doc {i}",
            category_id=category2_id,
            subcategory_id=uow.test_subcategory_id,
            stage_id=uow.test_stage_id,
            assigned_to=user1_id,
            created_by=uow.test_user_id,
            archive=False,
            created_at=datetime.now(),
        )
        doc.category = uow.category_repository.categories[category2_id]
        doc.subcategory = uow.subcategory_repository.subcategories[
            uow.test_subcategory_id
        ]
        doc.stage = uow.stage_repository.stages[uow.test_stage_id]
        doc.creator = uow.user_repository.users[uow.test_user_id]
        doc.assigned_user = uow.user_repository.users[user1_id]
        doc.tags = []
        uow.document_repository.documents[doc_id] = doc

    # Get documents for user1 filtered by category 1
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(
            **{
                "page": 1,
                "page_size": 10,
                "category_id": uow.test_category_id,
            }
        ),
        user_id=user1_id,
    )

    assert not isinstance(result, Error)
    # Should only see 3 documents from category 1
    assert result.total_rows == 3
    assert all(doc.category_id == uow.test_category_id for doc in result.data)
    assert all(doc.assigned_to == user1_id for doc in result.data)


@pytest.mark.asyncio
async def test_delete_document_success(document_service, uow):
    """Test deleting a document successfully."""
    from configuration.models import Tag

    # Create test tags
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document first
    document_data = DocumentCreate(
        name="Document to Delete",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("delete_test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Verify document exists
    assert document_id in uow.document_repository.documents

    # Delete the document
    result = await document_service.delete_document(document_id, uow.test_user_id)

    # Verify successful deletion
    assert not isinstance(result, Error)
    assert result.detail == "Document deleted successfully"
    assert document_id not in uow.document_repository.documents


@pytest.mark.asyncio
async def test_delete_document_not_found(document_service, uow):
    """Test deleting a non-existent document."""
    non_existent_id = uuid4()

    result = await document_service.delete_document(non_existent_id, uow.test_user_id)

    assert isinstance(result, Error)
    assert result.code == 404
    assert result.detail == "Document not found"


@pytest.mark.asyncio
async def test_get_document_by_id_success(document_service, uow):
    """Test retrieving a document by ID successfully."""
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document
    document_data = DocumentCreate(
        name="Test Document",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        description="Test description",
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Retrieve the document by ID
    result = await document_service.get_document_by_id(document_id)

    # Verify successful retrieval
    assert not isinstance(result, Error)
    assert result.id == document_id
    assert result.name == "Test Document"
    assert result.description == "Test description"
    assert result.category_id == uow.test_category_id
    assert result.subcategory_id == uow.test_subcategory_id
    assert result.stage_id == uow.test_stage_id
    assert result.assigned_to == uow.test_user_id
    assert result.created_by == uow.test_user_id
    assert len(result.tags) == 1
    assert result.tags[0].id == tag_id


@pytest.mark.asyncio
async def test_get_document_by_id_not_found(document_service):
    """Test retrieving a non-existent document by ID."""
    non_existent_id = uuid4()

    result = await document_service.get_document_by_id(non_existent_id)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert result.detail == "Document not found"


@pytest.mark.asyncio
async def test_get_version_history_success(document_service, uow):
    """Test retrieving version history for a document."""
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document
    document_data = DocumentCreate(
        name="Document with Versions",
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

    # Get version history
    result = await document_service.get_version_history(document_id)

    # Verify versions retrieved
    assert not isinstance(result, Error)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].document_id == document_id
    assert result[0].version_number == 1
    assert result[0].is_current is True


@pytest.mark.asyncio
async def test_get_version_history_not_found(document_service):
    """Test retrieving version history for non-existent document."""
    non_existent_id = uuid4()

    result = await document_service.get_version_history(non_existent_id)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert result.detail == "Document not found"


@pytest.mark.asyncio
async def test_get_version_history_empty(document_service, uow):
    """Test retrieving version history when no versions exist."""
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document
    document_data = DocumentCreate(
        name="Document No Versions",
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

    # Manually clear version histories to simulate empty state
    uow.document_repository.version_histories.clear()

    # Get version history
    result = await document_service.get_version_history(document_id)

    # Should return empty list
    assert not isinstance(result, Error)
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_create_new_version_success(document_service, uow):
    """Test creating a new version for a document."""
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document first
    document_data = DocumentCreate(
        name="Document for New Version",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("test_v1.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Verify initial version exists
    versions = await document_service.get_version_history(document_id)
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].is_current is True

    # Create new version
    new_version_file = create_upload_file("test_v2.pdf", b"new version content")
    result = await document_service.create_new_version(
        document_id, new_version_file, uow.test_user_id
    )

    # Verify new version created
    assert not isinstance(result, Error)
    assert result.version_number == 2
    assert result.is_current is True
    assert result.document_id == document_id
    assert result.created_by == uow.test_user_id

    # Verify version history updated
    updated_versions = await document_service.get_version_history(document_id)
    assert len(updated_versions) == 2

    # Check that old version is no longer current
    old_version = next(v for v in updated_versions if v.version_number == 1)
    assert old_version.is_current is False

    # Check that new version is current
    new_version = next(v for v in updated_versions if v.version_number == 2)
    assert new_version.is_current is True


@pytest.mark.asyncio
async def test_create_new_version_document_not_found(document_service):
    """Test creating a new version for non-existent document."""
    non_existent_id = uuid4()
    upload_file = create_upload_file("test.pdf")

    result = await document_service.create_new_version(
        non_existent_id, upload_file, uuid4()
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert result.detail == "Document not found"


@pytest.mark.asyncio
async def test_create_new_version_invalid_file_type(document_service, uow):
    """Test creating a new version with invalid file type."""
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document first
    document_data = DocumentCreate(
        name="Document for Invalid Version",
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

    # Try to upload invalid file type
    invalid_file = create_upload_file("test.exe", b"invalid content")
    result = await document_service.create_new_version(
        document_id, invalid_file, uow.test_user_id
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "not allowed" in result.detail.lower()


@pytest.mark.asyncio
async def test_create_new_version_multiple_versions(document_service, uow):
    """Test creating multiple versions increments version numbers correctly."""
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document
    document_data = DocumentCreate(
        name="Document Multiple Versions Test",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("test_v1.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Create version 2
    version2_file = create_upload_file("test_v2.pdf")
    version2 = await document_service.create_new_version(
        document_id, version2_file, uow.test_user_id
    )
    assert not isinstance(version2, Error)
    assert version2.version_number == 2

    # Create version 3
    version3_file = create_upload_file("test_v3.pdf")
    version3 = await document_service.create_new_version(
        document_id, version3_file, uow.test_user_id
    )
    assert not isinstance(version3, Error)
    assert version3.version_number == 3

    # Verify all versions exist
    all_versions = await document_service.get_version_history(document_id)
    assert len(all_versions) == 3

    # Only version 3 should be current
    current_versions = [v for v in all_versions if v.is_current]
    assert len(current_versions) == 1
    assert current_versions[0].version_number == 3


@pytest.mark.asyncio
async def test_archive_document_success(document_service, uow):
    """Test archiving a document successfully."""
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document
    document_data = DocumentCreate(
        name="Document to Archive",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("archive_test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Verify document is not archived initially
    assert created_document.archive is False

    # Archive the document
    result = await document_service.archive_document(document_id, uow.test_user_id)

    # Verify successful archiving
    assert not isinstance(result, Error)
    assert result.archive is True
    assert result.id == document_id

    # Verify document history was created
    history_entries = uow.history_repository.document_histories
    archive_history = [
        h for h in history_entries.values() if h.action == "Document Archive"
    ]
    assert len(archive_history) > 0
    assert "archived" in archive_history[-1].description.lower()


@pytest.mark.asyncio
async def test_archive_document_toggle(document_service, uow):
    """Test that archiving toggles the archive status."""
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document
    document_data = DocumentCreate(
        name="Document to Toggle Archive",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    upload_file = create_upload_file("toggle_test.pdf")
    created_document = await document_service.create_document(
        document_data, upload_file, uow.test_user_id
    )

    assert not isinstance(created_document, Error)
    document_id = created_document.id

    # Initially not archived
    assert created_document.archive is False

    # Archive the document (first toggle)
    result1 = await document_service.archive_document(document_id, uow.test_user_id)
    assert not isinstance(result1, Error)
    assert result1.archive is True

    # Unarchive the document (second toggle)
    result2 = await document_service.archive_document(document_id, uow.test_user_id)
    assert not isinstance(result2, Error)
    assert result2.archive is False

    # Archive again (third toggle)
    result3 = await document_service.archive_document(document_id, uow.test_user_id)
    assert not isinstance(result3, Error)
    assert result3.archive is True


@pytest.mark.asyncio
async def test_archive_document_not_found(document_service, uow):
    """Test archiving a non-existent document."""
    non_existent_id = uuid4()

    result = await document_service.archive_document(non_existent_id, uow.test_user_id)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert result.detail == "Document not found"


@pytest.mark.asyncio
async def test_get_documents_excludes_archived_by_default(document_service, uow):
    """Test that get_documents excludes archived documents by default."""
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create non-archived documents
    for i in range(3):
        document_data = DocumentCreate(
            name=f"Non-Archived Document {i}",
            category_id=uow.test_category_id,
            subcategory_id=uow.test_subcategory_id,
            stage_id=uow.test_stage_id,
            assigned_to=uow.test_user_id,
            tag_ids=[tag_id],
        )
        upload_file = create_upload_file(f"non_archived_{i}.pdf")
        await document_service.create_document(
            document_data, upload_file, uow.test_user_id
        )

    # Create and archive documents
    for i in range(2):
        document_data = DocumentCreate(
            name=f"Archived Document {i}",
            category_id=uow.test_category_id,
            subcategory_id=uow.test_subcategory_id,
            stage_id=uow.test_stage_id,
            assigned_to=uow.test_user_id,
            tag_ids=[tag_id],
        )
        upload_file = create_upload_file(f"archived_{i}.pdf")
        created = await document_service.create_document(
            document_data, upload_file, uow.test_user_id
        )
        # Archive the document
        await document_service.archive_document(created.id, uow.test_user_id)

    # Get documents without specifying archive parameter (should default to False)
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(**{"page": 1, "page_size": 10}),
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 3
    assert result.total_rows == 3
    # Verify all returned documents are not archived
    assert all(doc.archive is False for doc in result.data)


@pytest.mark.asyncio
async def test_get_documents_with_archive_filter_true(document_service, uow):
    """Test that get_documents returns archived documents when archive=True."""
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create non-archived documents
    for i in range(2):
        document_data = DocumentCreate(
            name=f"Non-Archived Document {i}",
            category_id=uow.test_category_id,
            subcategory_id=uow.test_subcategory_id,
            stage_id=uow.test_stage_id,
            assigned_to=uow.test_user_id,
            tag_ids=[tag_id],
        )
        upload_file = create_upload_file(f"non_archived_{i}.pdf")
        await document_service.create_document(
            document_data, upload_file, uow.test_user_id
        )

    # Create and archive documents
    for i in range(3):
        document_data = DocumentCreate(
            name=f"Archived Document {i}",
            category_id=uow.test_category_id,
            subcategory_id=uow.test_subcategory_id,
            stage_id=uow.test_stage_id,
            assigned_to=uow.test_user_id,
            tag_ids=[tag_id],
        )
        upload_file = create_upload_file(f"archived_{i}.pdf")
        created = await document_service.create_document(
            document_data, upload_file, uow.test_user_id
        )
        # Archive the document
        await document_service.archive_document(created.id, uow.test_user_id)

    # Get archived documents
    result = await document_service.get_all_documents_paginated(
        filters=DocumentFilterParams(
            **{
                "page": 1,
                "page_size": 10,
                "archive": True,
            }
        ),
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 3
    assert result.total_rows == 3
    # Verify all returned documents are archived
    assert all(doc.archive is True for doc in result.data)


@pytest.mark.asyncio
async def test_create_comment_success(document_service, uow):
    """Test creating a comment on a document successfully."""
    from configuration.models import Tag
    from core.documents.schemas import DocumentCommentCreate

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document first
    document_data = DocumentCreate(
        name="Document for Comment",
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

    # Create a comment
    comment_create = DocumentCommentCreate(comment="This is a test comment")
    result = await document_service.create_comment(
        document_id=document_id,
        comment_create=comment_create,
        current_user_id=uow.test_user_id,
    )

    # Verify comment created
    assert not isinstance(result, Error)
    assert result.comment == "This is a test comment"
    assert result.document_id == document_id
    assert result.user_id == uow.test_user_id
    assert result.user.id == uow.test_user_id

    # Verify document history was created
    history_entries = uow.history_repository.document_histories
    comment_history = [
        h for h in history_entries.values() if h.action == "Comment Create"
    ]
    assert len(comment_history) > 0
    assert "comment created" in comment_history[-1].description.lower()


@pytest.mark.asyncio
async def test_create_comment_document_not_found(document_service):
    """Test creating a comment on non-existent document."""
    from core.documents.schemas import DocumentCommentCreate

    non_existent_id = uuid4()
    comment_create = DocumentCommentCreate(comment="Test comment")

    result = await document_service.create_comment(
        document_id=non_existent_id,
        comment_create=comment_create,
        current_user_id=uuid4(),
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert result.detail == "Document not found"


@pytest.mark.asyncio
async def test_create_comment_empty_comment_fails(document_service, uow):
    """Test that empty comment fails validation."""
    from pydantic import ValidationError

    from configuration.models import Tag
    from core.documents.schemas import DocumentCommentCreate

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document
    document_data = DocumentCreate(
        name="Document for Empty Comment",
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

    # Try to create comment with empty string
    with pytest.raises(ValidationError):
        DocumentCommentCreate(comment="")


@pytest.mark.asyncio
async def test_create_multiple_comments_on_same_document(document_service, uow):
    """Test creating multiple comments on the same document."""
    from configuration.models import Tag
    from core.documents.schemas import DocumentCommentCreate

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document
    document_data = DocumentCreate(
        name="Document for Multiple Comments",
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

    # Create first comment
    comment1_create = DocumentCommentCreate(comment="First comment")
    result1 = await document_service.create_comment(
        document_id=document_id,
        comment_create=comment1_create,
        current_user_id=uow.test_user_id,
    )

    assert not isinstance(result1, Error)
    assert result1.comment == "First comment"

    # Create second comment
    comment2_create = DocumentCommentCreate(comment="Second comment")
    result2 = await document_service.create_comment(
        document_id=document_id,
        comment_create=comment2_create,
        current_user_id=uow.test_user_id,
    )

    assert not isinstance(result2, Error)
    assert result2.comment == "Second comment"

    # Verify both comments exist
    assert result1.id != result2.id
    assert result1.document_id == result2.document_id == document_id


@pytest.mark.asyncio
async def test_get_document_comments_success(document_service, uow):
    """Test retrieving comments for a document successfully."""
    from configuration.models import Tag
    from core.documents.schemas import DocumentCommentCreate

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document first
    document_data = DocumentCreate(
        name="Document with Comments",
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

    # Create multiple comments
    comment1_create = DocumentCommentCreate(comment="First comment")
    await document_service.create_comment(
        document_id=document_id,
        comment_create=comment1_create,
        current_user_id=uow.test_user_id,
    )

    comment2_create = DocumentCommentCreate(comment="Second comment")
    await document_service.create_comment(
        document_id=document_id,
        comment_create=comment2_create,
        current_user_id=uow.test_user_id,
    )

    comment3_create = DocumentCommentCreate(comment="Third comment")
    await document_service.create_comment(
        document_id=document_id,
        comment_create=comment3_create,
        current_user_id=uow.test_user_id,
    )

    # Get comments for the document
    result = await document_service.get_document_comments(document_id=document_id)

    # Verify comments retrieved
    assert not isinstance(result, Error)
    assert isinstance(result, list)
    assert len(result) == 3

    # Verify comments are ordered by created_at ascending (oldest first, newest last)
    assert result[0].comment == "First comment"
    assert result[1].comment == "Second comment"
    assert result[2].comment == "Third comment"

    # Verify all comments have the correct document_id
    assert all(c.document_id == document_id for c in result)

    # Verify all comments have user relationship populated
    assert all(c.user is not None for c in result)
    assert all(c.user_id == uow.test_user_id for c in result)


@pytest.mark.asyncio
async def test_get_document_comments_document_not_found(document_service):
    """Test retrieving comments for non-existent document."""
    non_existent_id = uuid4()

    result = await document_service.get_document_comments(document_id=non_existent_id)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert result.detail == "Document not found"


@pytest.mark.asyncio
async def test_get_document_comments_empty(document_service, uow):
    """Test retrieving comments when no comments exist."""
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document without comments
    document_data = DocumentCreate(
        name="Document No Comments",
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

    # Get comments (should be empty)
    result = await document_service.get_document_comments(document_id=document_id)

    # Should return empty list
    assert not isinstance(result, Error)
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_share_document_success(document_service, uow):
    """Test sharing a document with users successfully."""
    from auth.models import User
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create additional users to share with
    user1_id = uuid4()
    user2_id = uuid4()
    uow.user_repository.users[user1_id] = User(
        id=user1_id,
        first_name="User",
        last_name="One",
        username="user1",
        password="hashed",
        is_active=True,
    )
    uow.user_repository.users[user2_id] = User(
        id=user2_id,
        first_name="User",
        last_name="Two",
        username="user2",
        password="hashed",
        is_active=True,
    )

    # Create a document
    document_data = DocumentCreate(
        name="Document to Share",
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

    # Share the document
    share_data = ShareDocumentCreate(
        user_ids=[user1_id, user2_id],
        start_date="2024-01-01",
        end_date="2024-12-31",
    )

    result = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=uow.test_user_id,
    )

    # Verify shares created
    assert not isinstance(result, Error)
    assert len(result) == 2
    assert result[0].document_id == document_id
    assert result[0].user_id in [user1_id, user2_id]
    assert result[1].document_id == document_id
    assert result[1].user_id in [user1_id, user2_id]

    # Verify document history was created
    history_entries = uow.history_repository.document_histories
    share_history = [
        h for h in history_entries.values() if h.action == "Share Document"
    ]
    assert len(share_history) > 0
    assert "shared with users" in share_history[-1].description.lower()


@pytest.mark.asyncio
async def test_share_document_without_dates(document_service, uow):
    """Test sharing a document without start and end dates."""
    from auth.models import User
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create user to share with
    user_id = uuid4()
    uow.user_repository.users[user_id] = User(
        id=user_id,
        first_name="Test",
        last_name="User",
        username="shareuser",
        password="hashed",
        is_active=True,
    )

    # Create a document
    document_data = DocumentCreate(
        name="Document to Share Without Dates",
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

    # Share the document without dates
    share_data = ShareDocumentCreate(user_ids=[user_id])

    result = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=uow.test_user_id,
    )

    # Verify share created without dates
    assert not isinstance(result, Error)
    assert len(result) == 1
    assert result[0].start_date is None
    assert result[0].end_date is None


@pytest.mark.asyncio
async def test_share_document_invalid_date_range(document_service, uow):
    """Test sharing document with invalid date range fails."""
    from auth.models import User
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create user to share with
    user_id = uuid4()
    uow.user_repository.users[user_id] = User(
        id=user_id,
        first_name="Test",
        last_name="User",
        username="shareuser",
        password="hashed",
        is_active=True,
    )

    # Create a document
    document_data = DocumentCreate(
        name="Document with Invalid Date Range",
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

    # Try to share with end date before start date
    share_data = ShareDocumentCreate(
        user_ids=[user_id],
        start_date="2024-12-31",
        end_date="2024-01-01",
    )

    result = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=uow.test_user_id,
    )

    # Verify error
    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "start date must be before end date" in result.detail.lower()


@pytest.mark.asyncio
async def test_share_document_not_found(document_service, uow):
    """Test sharing non-existent document fails."""
    from auth.models import User

    # Create user to share with
    user_id = uuid4()
    uow.user_repository.users[user_id] = User(
        id=user_id,
        first_name="Test",
        last_name="User",
        username="shareuser",
        password="hashed",
        is_active=True,
    )

    non_existent_id = uuid4()
    share_data = ShareDocumentCreate(user_ids=[user_id])

    result = await document_service.share_document(
        document_id=non_existent_id,
        share_data=share_data,
        current_user_id=uow.test_user_id,
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "document not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_share_document_user_not_found(document_service, uow):
    """Test sharing document with non-existent user fails."""
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document
    document_data = DocumentCreate(
        name="Document to Share",
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

    # Try to share with non-existent user
    non_existent_user = uuid4()
    share_data = ShareDocumentCreate(user_ids=[non_existent_user])

    result = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=uow.test_user_id,
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "user not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_share_document_skip_duplicate(document_service, uow):
    """Test that sharing document with already shared user skips duplicate."""
    from auth.models import User
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create user to share with
    user_id = uuid4()
    uow.user_repository.users[user_id] = User(
        id=user_id,
        first_name="Test",
        last_name="User",
        username="shareuser",
        password="hashed",
        is_active=True,
    )

    # Create a document
    document_data = DocumentCreate(
        name="Document to Share Twice",
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

    # Share the document first time
    share_data = ShareDocumentCreate(user_ids=[user_id])
    result1 = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=uow.test_user_id,
    )

    assert not isinstance(result1, Error)
    assert len(result1) == 1

    # Try to share with same user again
    result2 = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=uow.test_user_id,
    )

    # Should skip duplicate and return empty list
    assert not isinstance(result2, Error)
    assert len(result2) == 0


@pytest.mark.asyncio
async def test_get_shared_users_success(document_service, uow):
    """Test getting shared users for a document."""
    from auth.models import User
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create users to share with
    user1_id = uuid4()
    user2_id = uuid4()
    uow.user_repository.users[user1_id] = User(
        id=user1_id,
        first_name="User",
        last_name="One",
        username="user1",
        password="hashed",
        is_active=True,
    )
    uow.user_repository.users[user2_id] = User(
        id=user2_id,
        first_name="User",
        last_name="Two",
        username="user2",
        password="hashed",
        is_active=True,
    )

    # Create a document
    document_data = DocumentCreate(
        name="Document to Get Shared Users",
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

    # Share the document
    share_data = ShareDocumentCreate(user_ids=[user1_id, user2_id])
    await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=uow.test_user_id,
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


@pytest.mark.asyncio
async def test_get_shared_users_document_not_found(document_service):
    """Test getting shared users for non-existent document."""
    non_existent_id = uuid4()

    result = await document_service.get_shared_users(document_id=non_existent_id)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "document not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_shared_users_empty(document_service, uow):
    """Test getting shared users when none exist."""
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document without sharing
    document_data = DocumentCreate(
        name="Document Without Shares",
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

    # Get shared users (should be empty)
    result = await document_service.get_shared_users(document_id=document_id)

    # Should return empty list
    assert not isinstance(result, Error)
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_delete_share_document_success(document_service, uow):
    """Test deleting a share document successfully."""
    from auth.models import User
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create user to share with
    user_id = uuid4()
    uow.user_repository.users[user_id] = User(
        id=user_id,
        first_name="Test",
        last_name="User",
        username="shareuser",
        password="hashed",
        is_active=True,
    )

    # Create a document
    document_data = DocumentCreate(
        name="Document to Share",
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

    # Share the document
    share_data = ShareDocumentCreate(user_ids=[user_id])
    share_result = await document_service.share_document(
        document_id=document_id,
        share_data=share_data,
        current_user_id=uow.test_user_id,
    )

    assert not isinstance(share_result, Error)
    assert len(share_result) == 1
    share_id = share_result[0].id

    # Delete the share
    result = await document_service.delete_share_document(
        document_id=document_id,
        share_id=share_id,
        current_user_id=uow.test_user_id,
    )

    # Verify deletion was successful
    assert not isinstance(result, Error)
    assert result.detail == "Assigned document successfully removed!"

    # Verify share was removed
    shares = await document_service.get_shared_users(document_id=document_id)
    assert not isinstance(shares, Error)
    assert len(shares) == 0

    # Verify document history was created
    history_entries = uow.history_repository.document_histories
    delete_history = [
        h for h in history_entries.values() if h.action == "Share Document Delete"
    ]
    assert len(delete_history) > 0
    assert "deleted" in delete_history[-1].description.lower()


@pytest.mark.asyncio
async def test_delete_share_document_not_found(document_service, uow):
    """Test deleting non-existent share document fails."""
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create a document
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
    document_id = created_document.id

    # Try to delete non-existent share
    non_existent_share_id = uuid4()
    result = await document_service.delete_share_document(
        document_id=document_id,
        share_id=non_existent_share_id,
        current_user_id=uow.test_user_id,
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "share not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_delete_share_document_document_not_found(document_service):
    """Test deleting share from non-existent document fails."""
    non_existent_document_id = uuid4()
    share_id = uuid4()

    result = await document_service.delete_share_document(
        document_id=non_existent_document_id,
        share_id=share_id,
        current_user_id=uuid4(),
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "document not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_delete_share_document_wrong_document(document_service, uow):
    """Test deleting share with mismatched document ID fails."""
    from auth.models import User
    from configuration.models import Tag

    # Create test tag
    tag_id = uuid4()
    uow.tag_repository.tags[tag_id] = Tag(id=tag_id, title="test-tag")

    # Create user to share with
    user_id = uuid4()
    uow.user_repository.users[user_id] = User(
        id=user_id,
        first_name="Test",
        last_name="User",
        username="shareuser",
        password="hashed",
        is_active=True,
    )

    # Create first document
    document_data1 = DocumentCreate(
        name="Document 1",
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

    assert not isinstance(created_document1, Error)
    document_id1 = created_document1.id

    # Create second document
    document_data2 = DocumentCreate(
        name="Document 2",
        category_id=uow.test_category_id,
        subcategory_id=uow.test_subcategory_id,
        stage_id=uow.test_stage_id,
        assigned_to=uow.test_user_id,
        tag_ids=[tag_id],
    )

    upload_file2 = create_upload_file("test2.pdf")
    created_document2 = await document_service.create_document(
        document_data2, upload_file2, uow.test_user_id
    )

    assert not isinstance(created_document2, Error)
    document_id2 = created_document2.id

    # Share document 1
    share_data = ShareDocumentCreate(user_ids=[user_id])
    share_result = await document_service.share_document(
        document_id=document_id1,
        share_data=share_data,
        current_user_id=uow.test_user_id,
    )

    assert not isinstance(share_result, Error)
    assert len(share_result) == 1
    share_id = share_result[0].id

    # Try to delete share using wrong document ID
    result = await document_service.delete_share_document(
        document_id=document_id2,  # Wrong document ID
        share_id=share_id,
        current_user_id=uow.test_user_id,
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "does not belong to this document" in result.detail.lower()


# ==================== Reminder Tests ====================
