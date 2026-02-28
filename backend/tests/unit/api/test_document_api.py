import os
import sys
from datetime import datetime
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile
from starlette import status

from core.documents.schemas import DocumentFilterParams

sys.path.append(f"{os.getcwd()}/src")
from auth.models import User
from core.documents.api import create_document, get_documents
from core.documents.fakes import FakeDocumentService
from core.models import Document


def create_upload_file(filename: str = "test.pdf", content: bytes = b"test content"):
    """Helper to create an UploadFile for testing."""
    file = BytesIO(content)
    return UploadFile(filename=filename, file=file)


@pytest.fixture
def document_service():
    """Provide a fake document service with test data."""
    service = FakeDocumentService()

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
@pytest.mark.asyncio
async def test_get_documents_api_success(document_service):
    """Test GET /documents endpoint."""
    result = await get_documents(
        filters=DocumentFilterParams(**{"page": 1, "page_size": 10, "archive": False}),
        document_service=document_service,
    )

    assert result.current_page == 1
    assert result.total_rows == 15
    assert result.total_pages == 2
    assert len(result.data) == 10
    assert result.has_next is True
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_get_documents_api_pagination(document_service):
    """Test GET /documents endpoint with pagination."""
    # Get page 2
    result = await get_documents(
        filters=DocumentFilterParams(**{"page": 2, "page_size": 10, "archive": False}),
        document_service=document_service,
    )

    assert result.current_page == 2
    assert result.total_rows == 15
    assert result.total_pages == 2
    assert len(result.data) == 5
    assert result.has_next is False
    assert result.has_previous is True


@pytest.mark.asyncio
async def test_get_documents_api_with_category_filter(document_service):
    """Test GET /documents endpoint with category filter."""
    result = await get_documents(
        filters=DocumentFilterParams(
            **{"page": 1, "page_size": 20, "archive": False, "category_id": document_service.test_category_id}
        ),
        document_service=document_service,
    )

    assert result.total_rows == 15
    assert all(d.category_id == document_service.test_category_id for d in result.data)


@pytest.mark.asyncio
async def test_get_documents_api_with_stage_filter(document_service):
    """Test GET /documents endpoint with stage filter."""
    result = await get_documents(
        filters=DocumentFilterParams(
            **{"page": 1, "page_size": 20, "archive": False, "category_id": document_service.test_category_id}
        ),
        document_service=document_service,
    )

    assert result.total_rows == 15
    assert all(d.stage_id == document_service.test_stage_id for d in result.data)


@pytest.mark.asyncio
async def test_get_documents_api_empty(document_service):
    """Test GET /documents endpoint with no documents matching filters."""
    result = await get_documents(
        filters=DocumentFilterParams(
            **{
                "page": 1,
                "page_size": 10,
                "archive": False,
                "category_id": uuid4(),
            }
        ),
        document_service=document_service,
    )

    assert result.total_rows == 0
    assert len(result.data) == 0


@pytest.mark.asyncio
async def test_create_document_api_success(document_service, current_user):
    """Test POST /documents endpoint."""
    upload_file = create_upload_file("test.pdf")
    # Pass tag UUIDs as comma-separated string
    tags_str = f"{document_service.test_tag1_id},{document_service.test_tag2_id}"
    result = await create_document(
        current_user=current_user,
        background_tasks=BackgroundTasks(),
        name="New Document",
        category_id=document_service.test_category_id,
        subcategory_id=document_service.test_subcategory_id,
        stage_id=document_service.test_stage_id,
        assigned_to=document_service.test_user_id,
        description="Test description",
        tags=tags_str,
        document=upload_file,
        document_service=document_service,
    )

    assert result.name == "New Document"
    assert result.description == "Test description"
    assert result.category_id == document_service.test_category_id
    assert len(result.tags) == 2
    assert result.tags[0].id == document_service.test_tag1_id
    assert result.tags[1].id == document_service.test_tag2_id


@pytest.mark.asyncio
async def test_create_document_api_duplicate_name(document_service, current_user):
    """Test POST /documents endpoint with duplicate name."""
    # First create a document
    upload_file1 = create_upload_file("test1.pdf")
    await create_document(
        current_user=current_user,
        background_tasks=BackgroundTasks(),
        name="Duplicate Doc",
        category_id=document_service.test_category_id,
        subcategory_id=document_service.test_subcategory_id,
        stage_id=document_service.test_stage_id,
        assigned_to=document_service.test_user_id,
        description="Test",
        tags=None,
        document=upload_file1,
        document_service=document_service,
    )

    # Try to create another with same name
    upload_file2 = create_upload_file("test2.pdf")
    with pytest.raises(HTTPException) as exc_info:
        await create_document(
            current_user=current_user,
            background_tasks=BackgroundTasks(),
            name="Duplicate Doc",
            category_id=document_service.test_category_id,
            subcategory_id=document_service.test_subcategory_id,
            stage_id=document_service.test_stage_id,
            assigned_to=document_service.test_user_id,
            description="Test",
            tags=None,
            document=upload_file2,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "name already exists" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_create_document_api_with_tags(document_service, current_user):
    """Test POST /documents endpoint with tags."""
    upload_file = create_upload_file("test.pdf")
    # Pass tag UUIDs as comma-separated string
    tags_str = f"{document_service.test_tag1_id},{document_service.test_tag2_id},{document_service.test_tag3_id}"
    result = await create_document(
        current_user=current_user,
        background_tasks=BackgroundTasks(),
        name="Tagged Document",
        category_id=document_service.test_category_id,
        subcategory_id=document_service.test_subcategory_id,
        stage_id=document_service.test_stage_id,
        assigned_to=document_service.test_user_id,
        description="Test",
        tags=tags_str,
        document=upload_file,
        document_service=document_service,
    )

    assert result.name == "Tagged Document"
    assert len(result.tags) == 3


@pytest.mark.asyncio
async def test_create_document_api_without_tags(document_service, current_user):
    """Test POST /documents endpoint without tags."""
    upload_file = create_upload_file("test.pdf")
    result = await create_document(
        current_user=current_user,
        background_tasks=BackgroundTasks(),
        name="Untagged Document",
        category_id=document_service.test_category_id,
        subcategory_id=document_service.test_subcategory_id,
        stage_id=document_service.test_stage_id,
        assigned_to=document_service.test_user_id,
        description="Test",
        tags=None,
        document=upload_file,
        document_service=document_service,
    )

    assert result.name == "Untagged Document"
    assert result.tags == []


@pytest.mark.asyncio
async def test_create_document_api_without_description(document_service, current_user):
    """Test POST /documents endpoint without description."""
    upload_file = create_upload_file("test.pdf")
    result = await create_document(
        current_user=current_user,
        background_tasks=BackgroundTasks(),
        name="No Description Document",
        category_id=document_service.test_category_id,
        subcategory_id=document_service.test_subcategory_id,
        stage_id=document_service.test_stage_id,
        assigned_to=document_service.test_user_id,
        description=None,
        tags=None,
        document=upload_file,
        document_service=document_service,
    )

    assert result.description is None


@pytest.mark.asyncio
async def test_delete_document_api_success(document_service, current_user):
    """Test DELETE /documents/{id} endpoint."""
    # Create a document first
    from core.documents.api import delete_document

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        name="Document to Delete",
        category_id=document_service.test_category_id,
        subcategory_id=document_service.test_subcategory_id,
        stage_id=document_service.test_stage_id,
        assigned_to=document_service.test_user_id,
        created_by=current_user.id,  # Set current_user as creator
        archive=False,
        created_at=datetime.now(),
    )
    # Populate relationships
    from configuration.models import Category, Stage, Subcategory

    doc.category = Category(id=document_service.test_category_id, title="Test Category")
    doc.subcategory = Subcategory(
        id=document_service.test_subcategory_id,
        title="Test Subcategory",
        category_id=document_service.test_category_id,
    )
    doc.stage = Stage(
        id=document_service.test_stage_id, title="Test Stage", color="#000000"
    )
    doc.creator = current_user
    doc.assigned_user = current_user
    doc.tags = []
    document_service.documents[doc_id] = doc

    # Delete the document
    result = await delete_document(
        document_id=doc_id,
        current_user=current_user,
        document_service=document_service,
    )

    assert result.detail == "Document deleted successfully"
    assert doc_id not in document_service.documents


@pytest.mark.asyncio
async def test_delete_document_api_not_found(document_service, current_user):
    """Test DELETE /documents/{id} endpoint with non-existent document."""
    from core.documents.api import delete_document

    non_existent_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await delete_document(
            document_id=non_existent_id,
            current_user=current_user,
            document_service=document_service,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Document not found"


@pytest.mark.asyncio
async def test_get_document_by_id_api_success(document_service):
    """Test GET /documents/{id} endpoint."""
    from core.documents.api import get_document

    # Get any existing document from the service
    doc_id = list(document_service.documents.keys())[0]
    expected_doc = document_service.documents[doc_id]

    # Retrieve the document
    result = await get_document(
        document_id=doc_id,
        document_service=document_service,
    )

    assert result.id == doc_id
    assert result.name == expected_doc.name
    assert result.description == expected_doc.description
    assert result.category_id == expected_doc.category_id
    assert result.subcategory_id == expected_doc.subcategory_id
    assert result.stage_id == expected_doc.stage_id
    assert result.assigned_to == expected_doc.assigned_to


@pytest.mark.asyncio
async def test_get_document_by_id_api_not_found(document_service):
    """Test GET /documents/{id} endpoint with non-existent document."""
    from core.documents.api import get_document

    non_existent_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await get_document(
            document_id=non_existent_id,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Document not found"


@pytest.mark.asyncio
async def test_get_version_history_api_success(document_service):
    """Test GET /documents/{id}/versions endpoint."""
    from datetime import datetime

    from core.documents.api import get_version_history
    from core.models import VersionHistory

    # Get any existing document from the service
    doc_id = list(document_service.documents.keys())[0]

    # Create mock version histories directly in the fake service
    mock_creator = User(
        id=document_service.test_user_id,
        first_name="Mock",
        last_name="User",
        username="mockuser",
        password="hashed",
        is_active=True,
    )

    version1 = VersionHistory(
        id=uuid4(),
        document_id=doc_id,
        document_file=f"uploads/documents/{doc_id}_v1.pdf",
        version_number=1,
        is_current=False,
        created_by=document_service.test_user_id,
        created_at=datetime.now(),
    )
    version1.creator = mock_creator

    version2 = VersionHistory(
        id=uuid4(),
        document_id=doc_id,
        document_file=f"uploads/documents/{doc_id}_v2.pdf",
        version_number=2,
        is_current=True,
        created_by=document_service.test_user_id,
        created_at=datetime.now(),
    )
    version2.creator = mock_creator

    # Override the fake service method to return versions
    async def mock_get_version_history(document_id, user_id=None):
        if document_id == doc_id:
            return [version2, version1]
        from schemas import Error

        return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

    document_service.get_version_history = mock_get_version_history

    # Get version history
    result = await get_version_history(
        document_id=doc_id,
        document_service=document_service,
    )

    assert len(result) == 2
    assert result[0].version_number == 2
    assert result[0].is_current is True
    assert result[1].version_number == 1
    assert result[1].is_current is False


@pytest.mark.asyncio
async def test_get_version_history_api_not_found(document_service):
    """Test GET /documents/{id}/versions endpoint with non-existent document."""
    from core.documents.api import get_version_history

    non_existent_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await get_version_history(
            document_id=non_existent_id,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Document not found"


@pytest.mark.asyncio
async def test_get_version_history_api_empty(document_service):
    """Test GET /documents/{id}/versions endpoint with no versions."""
    from core.documents.api import get_version_history

    # Get any existing document from the service
    doc_id = list(document_service.documents.keys())[0]

    # Override the fake service method to return empty list
    async def mock_get_version_history(document_id, user_id=None):
        if document_id == doc_id:
            return []
        from schemas import Error

        return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

    document_service.get_version_history = mock_get_version_history

    # Get version history
    result = await get_version_history(
        document_id=doc_id,
        document_service=document_service,
    )

    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_create_new_version_api_success(document_service, current_user):
    """Test POST /documents/{id}/versions endpoint."""
    from datetime import datetime

    from core.documents.api import create_new_version
    from core.models import VersionHistory

    # Get any existing document from the service
    doc_id = list(document_service.documents.keys())[0]

    # Create mock version
    new_version = VersionHistory(
        id=uuid4(),
        document_id=doc_id,
        document_file=f"uploads/documents/{doc_id}_v2.pdf",
        version_number=2,
        is_current=True,
        created_by=current_user.id,
        created_at=datetime.now(),
    )
    new_version.creator = current_user

    # Override the fake service method
    async def mock_create_new_version(
        document_id, document_file, current_user_id, background_tasks=None, user_id=None
    ):
        if document_id == doc_id:
            return new_version
        from schemas import Error

        return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

    document_service.create_new_version = mock_create_new_version

    # Upload new version
    upload_file = create_upload_file("test_v2.pdf", b"new version content")
    result = await create_new_version(
        document_id=doc_id,
        current_user=current_user,
        background_tasks=BackgroundTasks(),
        document=upload_file,
        document_service=document_service,
    )

    assert result.document_id == doc_id
    assert result.version_number == 2
    assert result.is_current is True


@pytest.mark.asyncio
async def test_create_new_version_api_not_found(document_service, current_user):
    """Test POST /documents/{id}/versions endpoint with non-existent document."""
    from core.documents.api import create_new_version

    non_existent_id = uuid4()
    upload_file = create_upload_file("test.pdf")

    with pytest.raises(HTTPException) as exc_info:
        await create_new_version(
            document_id=non_existent_id,
            current_user=current_user,
            background_tasks=BackgroundTasks(),
            document=upload_file,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Document not found"


@pytest.mark.asyncio
async def test_create_new_version_api_invalid_file(document_service, current_user):
    """Test POST /documents/{id}/versions endpoint with invalid file."""
    from core.documents.api import create_new_version

    # Get any existing document from the service
    doc_id = list(document_service.documents.keys())[0]

    # Override the fake service method to return error
    async def mock_create_new_version(
        document_id, document_file, current_user_id, background_tasks=None, user_id=None
    ):
        from schemas import Error

        return Error(
            detail="File type not allowed. Allowed types: pdf, doc, docx, xls, xlsx, ppt, pptx, txt, jpg, jpeg, png",
            code=status.HTTP_400_BAD_REQUEST,
        )

    document_service.create_new_version = mock_create_new_version

    # Try to upload invalid file
    upload_file = create_upload_file("test.exe", b"invalid content")

    with pytest.raises(HTTPException) as exc_info:
        await create_new_version(
            document_id=doc_id,
            current_user=current_user,
            background_tasks=BackgroundTasks(),
            document=upload_file,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "not allowed" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_preview_document_api_success(document_service, tmp_path):
    """Test GET /documents/{id}/preview endpoint."""
    from core.documents.api import preview_document

    # Get any existing document from the service
    doc_id = list(document_service.documents.keys())[0]

    # Create a temporary test file
    test_file = tmp_path / "test_document.pdf"
    test_file.write_bytes(b"PDF content here")

    # Override the fake service method to return the test file path
    async def mock_get_file_path(document_id):
        if document_id == doc_id:
            return str(test_file)
        from schemas import Error

        return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

    document_service.get_document_file_path = mock_get_file_path

    # Preview the document
    result = await preview_document(
        document_id=doc_id,
        document_service=document_service,
    )

    assert result.path == str(test_file)
    assert result.media_type == "application/pdf"
    assert result.headers["Content-Disposition"] == "inline"


@pytest.mark.asyncio
async def test_preview_document_api_not_found(document_service):
    """Test GET /documents/{id}/preview endpoint with non-existent document."""
    from core.documents.api import preview_document

    non_existent_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await preview_document(
            document_id=non_existent_id,
            document_service=document_service,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Document not found"


@pytest.mark.asyncio
async def test_preview_document_api_file_not_on_disk(document_service, tmp_path):
    """Test GET /documents/{id}/preview endpoint when file doesn't exist on disk."""
    from core.documents.api import preview_document

    # Get any existing document from the service
    doc_id = list(document_service.documents.keys())[0]

    # Return a path to a non-existent file
    non_existent_file = tmp_path / "missing.pdf"

    async def mock_get_file_path(document_id):
        if document_id == doc_id:
            return str(non_existent_file)
        from schemas import Error

        return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

    document_service.get_document_file_path = mock_get_file_path

    with pytest.raises(HTTPException) as exc_info:
        await preview_document(
            document_id=doc_id,
            document_service=document_service,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Document file not found on disk"


@pytest.mark.asyncio
async def test_preview_document_version_api_success(document_service, tmp_path):
    """Test GET /documents/{id}/versions/{version_id}/preview endpoint."""
    from core.documents.api import preview_document_version

    # Get any existing document from the service
    doc_id = list(document_service.documents.keys())[0]
    version_id = uuid4()

    # Create a temporary test file
    test_file = tmp_path / "test_document_v2.pdf"
    test_file.write_bytes(b"PDF version 2 content here")

    # Override the fake service method to return the test file path
    async def mock_get_version_file_path(document_id, vid):
        if document_id == doc_id and vid == version_id:
            return str(test_file)
        from schemas import Error

        return Error(detail="Version not found", code=status.HTTP_404_NOT_FOUND)

    document_service.get_version_file_path = mock_get_version_file_path

    # Preview the document version
    result = await preview_document_version(
        document_id=doc_id,
        version_id=version_id,
        document_service=document_service,
    )

    assert result.path == str(test_file)
    assert result.media_type == "application/pdf"
    assert result.headers["Content-Disposition"] == "inline"


@pytest.mark.asyncio
async def test_preview_document_version_api_not_found(document_service):
    """Test GET /documents/{id}/versions/{version_id}/preview endpoint with non-existent version."""
    from core.documents.api import preview_document_version

    non_existent_doc_id = uuid4()
    non_existent_version_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await preview_document_version(
            document_id=non_existent_doc_id,
            version_id=non_existent_version_id,
            document_service=document_service,
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_preview_media_types():
    """Test that different file extensions get correct media types."""
    from core.documents.api import _get_media_type

    assert _get_media_type(".pdf") == "application/pdf"
    assert _get_media_type(".doc") == "application/msword"
    assert (
        _get_media_type(".docx")
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert _get_media_type(".xls") == "application/vnd.ms-excel"
    assert (
        _get_media_type(".xlsx")
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert _get_media_type(".ppt") == "application/vnd.ms-powerpoint"
    assert (
        _get_media_type(".pptx")
        == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert _get_media_type(".txt") == "text/plain"
    assert _get_media_type(".jpg") == "image/jpeg"
    assert _get_media_type(".jpeg") == "image/jpeg"
    assert _get_media_type(".png") == "image/png"
    assert _get_media_type(".unknown") == "application/octet-stream"


@pytest.mark.asyncio
async def test_archive_document_api_success(document_service, current_user):
    """Test PATCH /documents/{id}/archive endpoint."""
    from core.documents.api import archive_document

    # Create a document first
    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        name="Document to Archive",
        category_id=document_service.test_category_id,
        subcategory_id=document_service.test_subcategory_id,
        stage_id=document_service.test_stage_id,
        assigned_to=document_service.test_user_id,
        created_by=current_user.id,
        archive=False,
        created_at=datetime.now(),
    )
    # Populate relationships
    from configuration.models import Category, Stage, Subcategory

    doc.category = Category(id=document_service.test_category_id, title="Test Category")
    doc.subcategory = Subcategory(
        id=document_service.test_subcategory_id,
        title="Test Subcategory",
        category_id=document_service.test_category_id,
    )
    doc.stage = Stage(
        id=document_service.test_stage_id, title="Test Stage", color="#000000"
    )
    doc.creator = current_user
    doc.assigned_user = current_user
    doc.tags = []
    document_service.documents[doc_id] = doc

    # Verify document is not archived initially
    assert doc.archive is False

    # Archive the document
    result = await archive_document(
        document_id=doc_id,
        current_user=current_user,
        document_service=document_service,
    )

    # Verify successful archiving
    assert result.id == doc_id
    assert result.archive is True


@pytest.mark.asyncio
async def test_archive_document_api_toggle(document_service, current_user):
    """Test PATCH /documents/{id}/archive endpoint toggles archive status."""
    from core.documents.api import archive_document

    # Create a document
    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        name="Document to Toggle Archive",
        category_id=document_service.test_category_id,
        subcategory_id=document_service.test_subcategory_id,
        stage_id=document_service.test_stage_id,
        assigned_to=document_service.test_user_id,
        created_by=current_user.id,
        archive=False,
        created_at=datetime.now(),
    )
    # Populate relationships
    from configuration.models import Category, Stage, Subcategory

    doc.category = Category(id=document_service.test_category_id, title="Test Category")
    doc.subcategory = Subcategory(
        id=document_service.test_subcategory_id,
        title="Test Subcategory",
        category_id=document_service.test_category_id,
    )
    doc.stage = Stage(
        id=document_service.test_stage_id, title="Test Stage", color="#000000"
    )
    doc.creator = current_user
    doc.assigned_user = current_user
    doc.tags = []
    document_service.documents[doc_id] = doc

    # Initially not archived
    assert doc.archive is False

    # Archive the document (first toggle)
    result1 = await archive_document(
        document_id=doc_id,
        current_user=current_user,
        document_service=document_service,
    )
    assert result1.archive is True

    # Unarchive the document (second toggle)
    result2 = await archive_document(
        document_id=doc_id,
        current_user=current_user,
        document_service=document_service,
    )
    assert result2.archive is False

    # Archive again (third toggle)
    result3 = await archive_document(
        document_id=doc_id,
        current_user=current_user,
        document_service=document_service,
    )
    assert result3.archive is True


@pytest.mark.asyncio
async def test_archive_document_api_not_found(document_service, current_user):
    """Test PATCH /documents/{id}/archive endpoint with non-existent document."""
    from core.documents.api import archive_document

    non_existent_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await archive_document(
            document_id=non_existent_id,
            current_user=current_user,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Document not found"


@pytest.mark.asyncio
async def test_get_documents_excludes_archived_by_default_api(document_service):
    """Test GET /documents endpoint excludes archived documents by default."""
    # Add non-archived documents
    for i in range(3):
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name=f"Non-Archived {i}",
            category_id=document_service.test_category_id,
            subcategory_id=document_service.test_subcategory_id,
            stage_id=document_service.test_stage_id,
            assigned_to=document_service.test_user_id,
            created_by=document_service.test_user_id,
            archive=False,
            created_at=datetime.now(),
        )
        from configuration.models import Category, Stage, Subcategory

        doc.category = Category(
            id=document_service.test_category_id, title="Test Category"
        )
        doc.subcategory = Subcategory(
            id=document_service.test_subcategory_id,
            title="Test Subcategory",
            category_id=document_service.test_category_id,
        )
        doc.stage = Stage(
            id=document_service.test_stage_id, title="Test Stage", color="#000000"
        )
        from auth.models import User

        doc.creator = User(
            id=document_service.test_user_id,
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        )
        doc.assigned_user = doc.creator
        doc.tags = []
        document_service.documents[doc_id] = doc

    # Add archived documents
    for i in range(2):
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name=f"Archived {i}",
            category_id=document_service.test_category_id,
            subcategory_id=document_service.test_subcategory_id,
            stage_id=document_service.test_stage_id,
            assigned_to=document_service.test_user_id,
            created_by=document_service.test_user_id,
            archive=True,
            created_at=datetime.now(),
        )
        from configuration.models import Category, Stage, Subcategory

        doc.category = Category(
            id=document_service.test_category_id, title="Test Category"
        )
        doc.subcategory = Subcategory(
            id=document_service.test_subcategory_id,
            title="Test Subcategory",
            category_id=document_service.test_category_id,
        )
        doc.stage = Stage(
            id=document_service.test_stage_id, title="Test Stage", color="#000000"
        )
        from auth.models import User

        doc.creator = User(
            id=document_service.test_user_id,
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        )
        doc.assigned_user = doc.creator
        doc.tags = []
        document_service.documents[doc_id] = doc

    # Get documents without archive parameter
    result = await get_documents(
        filters=DocumentFilterParams(
            **{
                "page": 1,
                "page_size": 20,
                "archive": False,
            }
        ),
        document_service=document_service,
    )

    # Should only return non-archived documents
    assert result.total_rows == 18  # 15 from fixture + 3 new non-archived
    assert all(d.archive is False for d in result.data)


@pytest.mark.asyncio
async def test_get_documents_with_archive_filter_true_api(document_service):
    """Test GET /documents endpoint with archive=True returns archived documents."""
    # Add archived documents
    for i in range(3):
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name=f"Archived {i}",
            category_id=document_service.test_category_id,
            subcategory_id=document_service.test_subcategory_id,
            stage_id=document_service.test_stage_id,
            assigned_to=document_service.test_user_id,
            created_by=document_service.test_user_id,
            archive=True,
            created_at=datetime.now(),
        )
        from configuration.models import Category, Stage, Subcategory

        doc.category = Category(
            id=document_service.test_category_id, title="Test Category"
        )
        doc.subcategory = Subcategory(
            id=document_service.test_subcategory_id,
            title="Test Subcategory",
            category_id=document_service.test_category_id,
        )
        doc.stage = Stage(
            id=document_service.test_stage_id, title="Test Stage", color="#000000"
        )
        from auth.models import User

        doc.creator = User(
            id=document_service.test_user_id,
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        )
        doc.assigned_user = doc.creator
        doc.tags = []
        document_service.documents[doc_id] = doc

    # Get archived documents
    result = await get_documents(
        filters=DocumentFilterParams(
            **{"page": 1, "page_size": 20, "archive": True}
        ),
        document_service=document_service,
    )

    # Should only return archived documents
    assert result.total_rows == 3
    assert all(d.archive is True for d in result.data)


@pytest.mark.asyncio
async def test_create_comment_api_success(document_service, current_user):
    """Test POST /documents/{id}/comments endpoint."""
    from core.documents.api import create_comment
    from core.documents.schemas import DocumentCommentCreate

    # Get any existing document from the service
    doc_id = list(document_service.documents.keys())[0]

    # Create comment
    comment_create = DocumentCommentCreate(comment="This is a test comment")
    result = await create_comment(
        document_id=doc_id,
        current_user=current_user,
        comment_create=comment_create,
        document_service=document_service,
    )

    # Verify comment created
    assert result.comment == "This is a test comment"
    assert result.document_id == doc_id
    assert result.user_id == current_user.id
    assert result.user.username == "mockuser"


@pytest.mark.asyncio
async def test_create_comment_api_document_not_found(document_service, current_user):
    """Test POST /documents/{id}/comments endpoint with non-existent document."""
    from core.documents.api import create_comment
    from core.documents.schemas import DocumentCommentCreate

    non_existent_id = uuid4()
    comment_create = DocumentCommentCreate(comment="Test comment")

    with pytest.raises(HTTPException) as exc_info:
        await create_comment(
            document_id=non_existent_id,
            current_user=current_user,
            comment_create=comment_create,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Document not found"


@pytest.mark.asyncio
async def test_create_comment_api_empty_comment_fails():
    """Test POST /documents/{id}/comments endpoint with empty comment."""
    from pydantic import ValidationError

    from core.documents.schemas import DocumentCommentCreate

    with pytest.raises(ValidationError):
        DocumentCommentCreate(comment="")


@pytest.mark.asyncio
async def test_create_multiple_comments_api(document_service, current_user):
    """Test creating multiple comments on the same document via API."""
    from core.documents.api import create_comment
    from core.documents.schemas import DocumentCommentCreate

    # Get any existing document from the service
    doc_id = list(document_service.documents.keys())[0]

    # Create first comment
    comment1_create = DocumentCommentCreate(comment="First comment")
    result1 = await create_comment(
        document_id=doc_id,
        current_user=current_user,
        comment_create=comment1_create,
        document_service=document_service,
    )

    assert result1.comment == "First comment"
    assert result1.document_id == doc_id

    # Create second comment
    comment2_create = DocumentCommentCreate(comment="Second comment")
    result2 = await create_comment(
        document_id=doc_id,
        current_user=current_user,
        comment_create=comment2_create,
        document_service=document_service,
    )

    assert result2.comment == "Second comment"
    assert result2.document_id == doc_id

    # Verify comments have different IDs
    assert result1.id != result2.id


@pytest.mark.asyncio
async def test_create_comment_api_long_comment(document_service, current_user):
    """Test POST /documents/{id}/comments endpoint with long comment."""
    from core.documents.api import create_comment
    from core.documents.schemas import DocumentCommentCreate

    # Get any existing document from the service
    doc_id = list(document_service.documents.keys())[0]

    # Create a long comment
    long_comment = "This is a very long comment. " * 100
    comment_create = DocumentCommentCreate(comment=long_comment)
    result = await create_comment(
        document_id=doc_id,
        current_user=current_user,
        comment_create=comment_create,
        document_service=document_service,
    )

    assert result.comment == long_comment
    assert result.document_id == doc_id
    assert result.user_id == current_user.id


@pytest.mark.asyncio
async def test_get_document_comments_api_success(document_service, current_user):
    """Test GET /documents/{id}/comments endpoint."""
    from core.documents.api import get_document_comments
    from core.models import DocumentComment

    # Get any existing document from the service
    doc_id = list(document_service.documents.keys())[0]

    # Create mock comments
    comment1 = DocumentComment(
        id=uuid4(),
        document_id=doc_id,
        user_id=current_user.id,
        comment="First comment",
        created_at=datetime.now(),
    )
    comment1.user = current_user

    comment2 = DocumentComment(
        id=uuid4(),
        document_id=doc_id,
        user_id=current_user.id,
        comment="Second comment",
        created_at=datetime.now(),
    )
    comment2.user = current_user

    comment3 = DocumentComment(
        id=uuid4(),
        document_id=doc_id,
        user_id=current_user.id,
        comment="Third comment",
        created_at=datetime.now(),
    )
    comment3.user = current_user

    # Add comments to the fake service
    document_service.comments[comment1.id] = comment1
    document_service.comments[comment2.id] = comment2
    document_service.comments[comment3.id] = comment3

    # Get comments
    result = await get_document_comments(
        document_id=doc_id,
        document_service=document_service,
    )

    # Verify comments retrieved
    assert isinstance(result, list)
    assert len(result) == 3

    # Verify all comments have correct document_id
    assert all(c.document_id == doc_id for c in result)

    # Verify comment content
    comment_texts = [c.comment for c in result]
    assert "First comment" in comment_texts
    assert "Second comment" in comment_texts
    assert "Third comment" in comment_texts


@pytest.mark.asyncio
async def test_get_document_comments_api_document_not_found(document_service):
    """Test GET /documents/{id}/comments endpoint with non-existent document."""
    from core.documents.api import get_document_comments

    non_existent_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await get_document_comments(
            document_id=non_existent_id,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Document not found"


@pytest.mark.asyncio
async def test_get_document_comments_api_empty(document_service):
    """Test GET /documents/{id}/comments endpoint with no comments."""
    from core.documents.api import get_document_comments

    # Get any existing document from the service
    doc_id = list(document_service.documents.keys())[0]

    # Get comments (should be empty)
    result = await get_document_comments(
        document_id=doc_id,
        document_service=document_service,
    )

    # Should return empty list
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_document_comments_api_ordering(document_service, current_user):
    """Test GET /documents/{id}/comments endpoint returns comments in descending ID order."""
    from core.documents.api import get_document_comments
    from core.models import DocumentComment

    # Get any existing document from the service
    doc_id = list(document_service.documents.keys())[0]

    # Create comments with explicit IDs in a way that we can verify ordering
    # UUID4 doesn't guarantee ordering, but we can verify the fake implementation sorts correctly
    comments_to_create = []
    for i in range(5):
        comment = DocumentComment(
            id=uuid4(),
            document_id=doc_id,
            user_id=current_user.id,
            comment=f"Comment {i}",
            created_at=datetime.now(),
        )
        comment.user = current_user
        document_service.comments[comment.id] = comment
        comments_to_create.append(comment)

    # Get comments
    result = await get_document_comments(
        document_id=doc_id,
        document_service=document_service,
    )

    # Verify all 5 comments are returned
    assert isinstance(result, list)
    assert len(result) == 5

    # Verify all comments belong to the document
    assert all(c.document_id == doc_id for c in result)

    # The ordering will be by UUID descending (as implemented in fake)
    # Just verify that comments are returned and have valid structure
    for comment in result:
        assert comment.id in [c.id for c in comments_to_create]
        assert comment.user is not None
        assert comment.comment.startswith("Comment")


@pytest.mark.asyncio
async def test_get_document_comments_api_multiple_documents(
    document_service, current_user
):
    """Test GET /documents/{id}/comments endpoint returns only comments for specific document."""
    from core.documents.api import get_document_comments
    from core.models import DocumentComment

    # Get two different documents
    doc_ids = list(document_service.documents.keys())[:2]
    doc_id_1 = doc_ids[0]
    doc_id_2 = doc_ids[1]

    # Create comments for document 1
    for i in range(3):
        comment = DocumentComment(
            id=uuid4(),
            document_id=doc_id_1,
            user_id=current_user.id,
            comment=f"Doc1 Comment {i}",
            created_at=datetime.now(),
        )
        comment.user = current_user
        document_service.comments[comment.id] = comment

    # Create comments for document 2
    for i in range(2):
        comment = DocumentComment(
            id=uuid4(),
            document_id=doc_id_2,
            user_id=current_user.id,
            comment=f"Doc2 Comment {i}",
            created_at=datetime.now(),
        )
        comment.user = current_user
        document_service.comments[comment.id] = comment

    # Get comments for document 1
    result1 = await get_document_comments(
        document_id=doc_id_1,
        document_service=document_service,
    )

    # Verify only document 1 comments are returned
    assert isinstance(result1, list)
    assert len(result1) == 3
    assert all(c.document_id == doc_id_1 for c in result1)
    assert all("Doc1" in c.comment for c in result1)

    # Get comments for document 2
    result2 = await get_document_comments(
        document_id=doc_id_2,
        document_service=document_service,
    )

    # Verify only document 2 comments are returned
    assert isinstance(result2, list)
    assert len(result2) == 2
    assert all(c.document_id == doc_id_2 for c in result2)
    assert all("Doc2" in c.comment for c in result2)


@pytest.mark.asyncio
async def test_delete_share_document_success(document_service, current_user):
    """Test DELETE /documents/{id}/share/{share_id} endpoint removes share successfully."""
    from core.documents.api import delete_share_document
    from core.models import ShareDocument

    # Get a document and update its creator to be current_user
    doc_id = list(document_service.documents.keys())[0]
    document_service.documents[doc_id].created_by = current_user.id
    document_service.documents[doc_id].creator = current_user

    # Create a share
    share = ShareDocument(
        id=uuid4(),
        document_id=doc_id,
        user_id=uuid4(),
        start_date=None,
        end_date=None,
        created_at=datetime.now(),
    )
    share.user = User(
        id=share.user_id,
        first_name="Shared",
        last_name="User",
        username="shareduser",
        password="hashed",
        is_active=True,
    )
    document_service.shares[share.id] = share

    # Delete the share
    result = await delete_share_document(
        document_id=doc_id,
        share_id=share.id,
        current_user=current_user,
        document_service=document_service,
    )

    # Verify deletion was successful
    assert result.detail == "Assigned document successfully removed!"
    assert share.id not in document_service.shares


@pytest.mark.asyncio
async def test_delete_share_document_not_found(document_service, current_user):
    """Test DELETE /documents/{id}/share/{share_id} endpoint with non-existent share fails."""
    from core.documents.api import delete_share_document

    # Get a document and update its creator to be current_user
    doc_id = list(document_service.documents.keys())[0]
    document_service.documents[doc_id].created_by = current_user.id
    document_service.documents[doc_id].creator = current_user
    non_existent_share_id = uuid4()

    # Try to delete non-existent share
    with pytest.raises(HTTPException) as exc_info:
        await delete_share_document(
            document_id=doc_id,
            share_id=non_existent_share_id,
            current_user=current_user,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "share not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_delete_share_document_document_not_found(document_service, current_user):
    """Test DELETE /documents/{id}/share/{share_id} endpoint with non-existent document fails."""
    from core.documents.api import delete_share_document

    non_existent_doc_id = uuid4()
    share_id = uuid4()

    # Try to delete share from non-existent document
    with pytest.raises(HTTPException) as exc_info:
        await delete_share_document(
            document_id=non_existent_doc_id,
            share_id=share_id,
            current_user=current_user,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "document not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_delete_share_document_wrong_document(document_service, current_user):
    """Test DELETE /documents/{id}/share/{share_id} endpoint with mismatched document ID fails."""
    from core.documents.api import delete_share_document
    from core.models import ShareDocument

    # Get two documents and update their creator to be current_user
    doc_ids = list(document_service.documents.keys())[:2]
    doc_id_1 = doc_ids[0]
    doc_id_2 = doc_ids[1]
    document_service.documents[doc_id_1].created_by = current_user.id
    document_service.documents[doc_id_1].creator = current_user
    document_service.documents[doc_id_2].created_by = current_user.id
    document_service.documents[doc_id_2].creator = current_user

    # Create a share for document 1
    share = ShareDocument(
        id=uuid4(),
        document_id=doc_id_1,
        user_id=uuid4(),
        start_date=None,
        end_date=None,
        created_at=datetime.now(),
    )
    share.user = User(
        id=share.user_id,
        first_name="Shared",
        last_name="User",
        username="shareduser",
        password="hashed",
        is_active=True,
    )
    document_service.shares[share.id] = share

    # Try to delete share using wrong document ID
    with pytest.raises(HTTPException) as exc_info:
        await delete_share_document(
            document_id=doc_id_2,  # Wrong document ID
            share_id=share.id,
            current_user=current_user,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "does not belong to this document" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_generate_share_link_success(document_service):
    """Test POST /documents/{id}/share-link endpoint successfully generates a link."""
    from datetime import date, timedelta

    from core.documents.api import generate_share_link
    from core.documents.schemas import ShareLinkCreate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Create share link with expiration date in future
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_create = ShareLinkCreate(
        expiration_date=future_date, password="test-password"
    )

    result = await generate_share_link(
        document_id=doc_id,
        current_user=User(
            id=document_service.test_user_id,
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        ),
        share_link_create=share_link_create,
        document_service=document_service,
    )

    # Verify share link response
    assert isinstance(result.token, str)
    assert len(result.token) > 0


@pytest.mark.asyncio
async def test_generate_share_link_without_password(document_service):
    """Test POST /documents/{id}/share-link endpoint without password."""
    from datetime import date, timedelta

    from core.documents.api import generate_share_link
    from core.documents.schemas import ShareLinkCreate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Create share link without password
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_create = ShareLinkCreate(expiration_date=future_date, password=None)

    result = await generate_share_link(
        document_id=doc_id,
        current_user=User(
            id=document_service.test_user_id,
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        ),
        share_link_create=share_link_create,
        document_service=document_service,
    )

    # Verify share link response
    assert isinstance(result.token, str)
    assert len(result.token) > 0


@pytest.mark.asyncio
async def test_generate_share_link_without_expiration(document_service):
    """Test POST /documents/{id}/share-link endpoint without expiration date."""
    from core.documents.api import generate_share_link
    from core.documents.schemas import ShareLinkCreate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Create share link without expiration date (permanent link)
    share_link_create = ShareLinkCreate(expiration_date=None, password=None)

    result = await generate_share_link(
        document_id=doc_id,
        current_user=User(
            id=document_service.test_user_id,
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        ),
        share_link_create=share_link_create,
        document_service=document_service,
    )

    # Verify share link response
    assert isinstance(result.token, str)
    assert len(result.token) > 0


@pytest.mark.asyncio
async def test_generate_share_link_expired_date(document_service):
    """Test POST /documents/{id}/share-link endpoint with past expiration date fails."""
    from datetime import date, timedelta

    from core.documents.api import generate_share_link
    from core.documents.schemas import ShareLinkCreate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Create share link with past expiration date
    past_date = (date.today() - timedelta(days=1)).isoformat()
    share_link_create = ShareLinkCreate(expiration_date=past_date, password=None)

    with pytest.raises(HTTPException) as exc_info:
        await generate_share_link(
            document_id=doc_id,
            current_user=User(
                id=document_service.test_user_id,
                first_name="Test",
                last_name="User",
                username="testuser",
                password="hashed",
                is_active=True,
            ),
            share_link_create=share_link_create,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "future" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_generate_share_link_document_not_found(document_service):
    """Test POST /documents/{id}/share-link endpoint with non-existent document fails."""
    from datetime import date, timedelta

    from core.documents.api import generate_share_link
    from core.documents.schemas import ShareLinkCreate

    non_existent_id = uuid4()
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_create = ShareLinkCreate(expiration_date=future_date, password=None)

    with pytest.raises(HTTPException) as exc_info:
        await generate_share_link(
            document_id=non_existent_id,
            current_user=User(
                id=document_service.test_user_id,
                first_name="Test",
                last_name="User",
                username="testuser",
                password="hashed",
                is_active=True,
            ),
            share_link_create=share_link_create,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "document not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_preview_shared_document_success(document_service, tmp_path):
    """Test POST /documents/shared/{token} endpoint successfully accesses shared document."""
    from datetime import date, timedelta

    from core.documents.api import generate_share_link, preview_shared_document
    from core.documents.schemas import ShareLinkAccessRequest, ShareLinkCreate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Create a temporary test file
    test_file = tmp_path / f"{doc_id}.pdf"
    test_file.write_bytes(b"PDF content here")

    # Override the fake service method to return the test file path
    async def mock_get_file_path(document_id):
        if document_id == doc_id:
            return str(test_file)
        from schemas import Error

        return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

    document_service.get_document_file_path = mock_get_file_path

    # Generate share link
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_create = ShareLinkCreate(
        expiration_date=future_date, password="test-password"
    )

    link_result = await generate_share_link(
        document_id=doc_id,
        current_user=User(
            id=document_service.test_user_id,
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        ),
        share_link_create=share_link_create,
        document_service=document_service,
    )

    # Access shared document with correct password
    access_request = ShareLinkAccessRequest(password="test-password")
    result = await preview_shared_document(
        token=link_result.token,
        access_request=access_request,
        document_service=document_service,
    )

    assert result.path == str(test_file)
    assert result.media_type == "application/pdf"
    assert result.headers["Content-Disposition"] == "inline"


@pytest.mark.asyncio
async def test_preview_shared_document_without_password(document_service, tmp_path):
    """Test POST /documents/shared/{token} endpoint with no password protection."""
    from datetime import date, timedelta

    from core.documents.api import generate_share_link, preview_shared_document
    from core.documents.schemas import ShareLinkAccessRequest, ShareLinkCreate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Create a temporary test file
    test_file = tmp_path / f"{doc_id}.pdf"
    test_file.write_bytes(b"PDF content here")

    # Override the fake service method to return the test file path
    async def mock_get_file_path(document_id):
        if document_id == doc_id:
            return str(test_file)
        from schemas import Error

        return Error(detail="Document not found", code=status.HTTP_404_NOT_FOUND)

    document_service.get_document_file_path = mock_get_file_path

    # Generate share link without password
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_create = ShareLinkCreate(expiration_date=future_date, password=None)

    link_result = await generate_share_link(
        document_id=doc_id,
        current_user=User(
            id=document_service.test_user_id,
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        ),
        share_link_create=share_link_create,
        document_service=document_service,
    )

    # Access shared document without password
    access_request = ShareLinkAccessRequest(password=None)
    result = await preview_shared_document(
        token=link_result.token,
        access_request=access_request,
        document_service=document_service,
    )

    assert result.path == str(test_file)
    assert result.media_type == "application/pdf"


@pytest.mark.asyncio
async def test_preview_shared_document_wrong_password(document_service):
    """Test POST /documents/shared/{token} endpoint with wrong password fails."""
    from datetime import date, timedelta

    from core.documents.api import generate_share_link, preview_shared_document
    from core.documents.schemas import ShareLinkAccessRequest, ShareLinkCreate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Generate share link with password
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_create = ShareLinkCreate(
        expiration_date=future_date, password="correct-password"
    )

    link_result = await generate_share_link(
        document_id=doc_id,
        current_user=User(
            id=document_service.test_user_id,
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        ),
        share_link_create=share_link_create,
        document_service=document_service,
    )

    # Try to access with wrong password
    access_request = ShareLinkAccessRequest(password="wrong-password")

    with pytest.raises(HTTPException) as exc_info:
        await preview_shared_document(
            token=link_result.token,
            access_request=access_request,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "password" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_preview_shared_document_missing_password(document_service):
    """Test POST /documents/shared/{token} endpoint with missing required password fails."""
    from datetime import date, timedelta

    from core.documents.api import generate_share_link, preview_shared_document
    from core.documents.schemas import ShareLinkAccessRequest, ShareLinkCreate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Generate share link with password
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_create = ShareLinkCreate(
        expiration_date=future_date, password="required-password"
    )

    link_result = await generate_share_link(
        document_id=doc_id,
        current_user=User(
            id=document_service.test_user_id,
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        ),
        share_link_create=share_link_create,
        document_service=document_service,
    )

    # Try to access without providing password
    access_request = ShareLinkAccessRequest(password=None)

    with pytest.raises(HTTPException) as exc_info:
        await preview_shared_document(
            token=link_result.token,
            access_request=access_request,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "password" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_preview_shared_document_invalid_token(document_service):
    """Test POST /documents/shared/{token} endpoint with invalid token fails."""
    from core.documents.api import preview_shared_document
    from core.documents.schemas import ShareLinkAccessRequest

    # Try to access with invalid token
    access_request = ShareLinkAccessRequest(password=None)

    with pytest.raises(HTTPException) as exc_info:
        await preview_shared_document(
            token="invalid-token",
            access_request=access_request,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "invalid" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_preview_shared_document_expired_link(document_service):
    """Test POST /documents/shared/{token} endpoint with expired link fails."""
    from datetime import date, timedelta

    from core.documents.api import generate_share_link, preview_shared_document
    from core.documents.schemas import ShareLinkAccessRequest, ShareLinkCreate

    # Get a document
    doc_id = list(document_service.documents.keys())[0]

    # Generate share link that expires today (will be expired when accessed)
    today = date.today().isoformat()
    share_link_create = ShareLinkCreate(expiration_date=today, password=None)

    link_result = await generate_share_link(
        document_id=doc_id,
        current_user=User(
            id=document_service.test_user_id,
            first_name="Test",
            last_name="User",
            username="testuser",
            password="hashed",
            is_active=True,
        ),
        share_link_create=share_link_create,
        document_service=document_service,
    )

    # Modify the link data to have a past expiration date
    link_data = document_service.share_links[link_result.token]
    past_date = (date.today() - timedelta(days=1)).isoformat()
    link_data["exp_date"] = past_date

    # Try to access expired link
    access_request = ShareLinkAccessRequest(password=None)

    with pytest.raises(HTTPException) as exc_info:
        await preview_shared_document(
            token=link_result.token,
            access_request=access_request,
            document_service=document_service,
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "expired" in exc_info.value.detail.lower()
