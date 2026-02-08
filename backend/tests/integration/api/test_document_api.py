import asyncio
import os
import sys
from io import BytesIO

import pytest
from httpx import AsyncClient
from sqlalchemy import select

sys.path.insert(0, f"{os.getcwd()}/src")

from configuration.models import Category, Stage, Subcategory  # noqa: E402
from core.models import Document, VersionHistory  # noqa: E402
from db import default_session_factory  # noqa: E402


async def create_test_data():
    """Helper to create test data (category, subcategory, stage, user)."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    async with default_session_factory() as session:
        # Create category
        category = Category(title="API Test Category")
        session.add(category)
        await session.flush()

        # Create subcategory
        subcategory = Subcategory(title="API Test Subcategory", category_id=category.id)
        session.add(subcategory)
        await session.flush()

        # Create stage
        stage = Stage(title="API Test Stage", color="#00FF00")
        session.add(stage)
        await session.flush()

        # Create assigned user
        user = User(
            first_name="Assigned",
            last_name="User",
            username="assigned_user_api_test",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.flush()

        await session.commit()

        return {
            "category_id": str(category.id),
            "subcategory_id": str(subcategory.id),
            "stage_id": str(stage.id),
            "user_id": str(user.id),
        }


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_create_document_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /api/v1/documents creates document."""
    from configuration.models import Tag
    from db import default_session_factory

    test_data = await create_test_data()

    # Create tags in database first
    async with default_session_factory() as session:
        tag1 = Tag(title="api")
        tag2 = Tag(title="test")
        tag3 = Tag(title="integration")
        session.add_all([tag1, tag2, tag3])
        await session.commit()
        await session.refresh(tag1)
        await session.refresh(tag2)
        await session.refresh(tag3)
        tag_ids_str = f"{tag1.id},{tag2.id},{tag3.id}"

    # Create multipart form data
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "API Test Document",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "API test description",
        "tags": tag_ids_str,
    }

    response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["name"] == "API Test Document"
    assert result["description"] == "API test description"
    assert len(result["tags"]) == 3
    assert "id" in result


@pytest.mark.asyncio
async def test_get_documents_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents returns paginated documents."""
    test_data = await create_test_data()

    # Create a test document first
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document for Listing",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    # Get documents
    response = await client.get(
        "/api/v1/documents?page=1&page_size=10",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    result = response.json()
    assert "data" in result
    assert "current_page" in result
    assert "total_rows" in result
    assert result["current_page"] == 1


@pytest.mark.asyncio
async def test_get_documents_with_category_filter(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents with category filter."""
    test_data = await create_test_data()

    # Create document
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Filtered Document",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    # Get documents with filter
    response = await client.get(
        f"/api/v1/documents?page=1&page_size=10&category_id={test_data['category_id']}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    result = response.json()
    assert len(result["data"]) > 0
    assert all(d["category_id"] == test_data["category_id"] for d in result["data"])


@pytest.mark.asyncio
async def test_get_documents_with_stage_filter(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents with stage filter."""
    test_data = await create_test_data()

    # Create document
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Stage Filtered Document",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    # Get documents with filter
    response = await client.get(
        f"/api/v1/documents?page=1&page_size=10&stage_id={test_data['stage_id']}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    result = response.json()
    assert len(result["data"]) > 0
    assert all(d["stage_id"] == test_data["stage_id"] for d in result["data"])


@pytest.mark.asyncio
async def test_create_document_duplicate_name_fails(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /api/v1/documents fails with duplicate name."""
    test_data = await create_test_data()

    # Create first document
    files1 = {"document": ("test1.pdf", BytesIO(b"test content 1"), "application/pdf")}
    data = {
        "name": "Duplicate Name Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    await client.post(
        "/api/v1/documents",
        data=data,
        files=files1,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    # Try to create second document with same name
    files2 = {"document": ("test2.pdf", BytesIO(b"test content 2"), "application/pdf")}
    response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files2,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 400
    assert "name already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_document_without_permission_fails(
    client: AsyncClient, user_without_permissions: str
):
    """Test POST /api/v1/documents fails without permission."""
    test_data = await create_test_data()

    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "No Permission Document",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_documents_without_permission_fails(
    client: AsyncClient, user_without_permissions: str
):
    """Test GET /api/v1/documents fails without permission."""
    response = await client.get(
        "/api/v1/documents?page=1&page_size=10",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_document_persists_in_database(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test that created document is actually in the database."""
    test_data = await create_test_data()

    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Database Persistence Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "Testing database persistence",
    }

    response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    result = response.json()
    document_id = result["id"]

    # Verify in database
    from uuid import UUID

    async with default_session_factory() as session:
        stmt = select(Document).where(Document.id == UUID(document_id))
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()

        assert db_document is not None
        assert db_document.name == "Database Persistence Test"
        assert db_document.description == "Testing database persistence"


@pytest.mark.asyncio
async def test_delete_document_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test DELETE /api/v1/documents/{id} endpoint."""
    test_data = await create_test_data()

    # Create a document first
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document to Delete",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Delete the document
    delete_response = await client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert delete_response.status_code == 200
    result = delete_response.json()
    assert result["detail"] == "Document deleted successfully"

    # Verify document is deleted by trying to get it (would return 404 if we had a GET endpoint)
    # For now, trying to delete again should return 404
    second_delete = await client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert second_delete.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test DELETE /api/v1/documents/{id} with non-existent document."""
    from uuid import uuid4

    non_existent_id = uuid4()

    response = await client.delete(
        f"/api/v1/documents/{non_existent_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.asyncio
async def test_delete_document_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test DELETE /api/v1/documents/{id} without required permission."""
    from uuid import uuid4

    # Try to delete without permission
    response = await client.delete(
        f"/api/v1/documents/{uuid4()}",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403
    # Check that it's a permission-related error
    detail = response.json()["detail"]
    assert "Access denied" in detail or "Permission denied" in detail


@pytest.mark.asyncio
async def test_get_document_by_id_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{id} endpoint."""
    test_data = await create_test_data()

    # Create a document first
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document to Get",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "Testing get by ID",
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Get the document by ID
    response = await client.get(
        f"/api/v1/documents/{document_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["id"] == document_id
    assert result["name"] == "Document to Get"
    assert result["description"] == "Testing get by ID"
    assert result["category_id"] == test_data["category_id"]
    assert result["subcategory_id"] == test_data["subcategory_id"]
    assert result["stage_id"] == test_data["stage_id"]
    assert result["assigned_to"] == test_data["user_id"]


@pytest.mark.asyncio
async def test_get_document_by_id_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{id} with non-existent document."""
    from uuid import uuid4

    non_existent_id = uuid4()

    response = await client.get(
        f"/api/v1/documents/{non_existent_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.asyncio
async def test_get_document_by_id_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test GET /api/v1/documents/{id} without required permission."""
    from uuid import uuid4

    # Try to get document without permission
    response = await client.get(
        f"/api/v1/documents/{uuid4()}",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403
    # Check that it's a permission-related error
    detail = response.json()["detail"]
    assert "Access denied" in detail or "Permission denied" in detail


@pytest.mark.asyncio
async def test_get_version_history_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{id}/versions endpoint."""
    test_data = await create_test_data()

    # Create a document first
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document with Versions",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "Testing version history",
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Get version history
    response = await client.get(
        f"/api/v1/documents/{document_id}/versions",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["document_id"] == document_id
    assert result[0]["version_number"] == 1
    assert result[0]["is_current"] is True
    assert "created_at" in result[0]
    assert "document_file" in result[0]


@pytest.mark.asyncio
async def test_get_version_history_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{id}/versions with non-existent document."""
    from uuid import uuid4

    non_existent_id = uuid4()

    response = await client.get(
        f"/api/v1/documents/{non_existent_id}/versions",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.asyncio
async def test_get_version_history_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test GET /api/v1/documents/{id}/versions without required permission."""
    from uuid import uuid4

    # Try to get version history without permission
    response = await client.get(
        f"/api/v1/documents/{uuid4()}/versions",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403
    # Check that it's a permission-related error
    detail = response.json()["detail"]
    assert "Access denied" in detail or "Permission denied" in detail


@pytest.mark.asyncio
async def test_get_version_history_multiple_versions(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{id}/versions with multiple versions."""

    from core.models import VersionHistory

    test_data = await create_test_data()

    # Create a document
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document Multiple Versions",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Add more versions directly to database
    from uuid import UUID

    async with default_session_factory() as session:
        await asyncio.sleep(0.1)

        version2 = VersionHistory(
            document_id=UUID(document_id),
            document_file=f"uploads/documents/{document_id}_v2.pdf",
            version_number=2,
            is_current=False,
            created_by=UUID(test_data["user_id"]),
        )
        session.add(version2)
        await session.flush()

        await asyncio.sleep(0.1)

        version3 = VersionHistory(
            document_id=UUID(document_id),
            document_file=f"uploads/documents/{document_id}_v3.pdf",
            version_number=3,
            is_current=False,
            created_by=UUID(test_data["user_id"]),
        )
        session.add(version3)
        await session.commit()

    # Get version history
    response = await client.get(
        f"/api/v1/documents/{document_id}/versions",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    result = response.json()
    assert len(result) == 3
    # Verify ordered newest first
    assert result[0]["version_number"] == 3
    assert result[1]["version_number"] == 2
    assert result[2]["version_number"] == 1


@pytest.mark.asyncio
async def test_create_new_version_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /api/v1/documents/{id}/versions endpoint."""
    test_data = await create_test_data()

    # Create a document first
    files = {"document": ("v1.pdf", BytesIO(b"version 1 content"), "application/pdf")}
    data = {
        "name": "Document New Version Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Upload new version
    version_files = {
        "document": ("v2.pdf", BytesIO(b"version 2 content"), "application/pdf")
    }
    response = await client.post(
        f"/api/v1/documents/{document_id}/versions",
        files=version_files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["document_id"] == document_id
    assert result["version_number"] == 2
    assert result["is_current"] is True
    assert "document_file" in result
    assert "created_at" in result

    # Verify in database
    from uuid import UUID

    async with default_session_factory() as session:
        stmt = (
            select(VersionHistory)
            .where(VersionHistory.document_id == UUID(document_id))
            .order_by(VersionHistory.version_number.desc())
        )
        db_result = await session.execute(stmt)
        versions = list(db_result.scalars().all())

        assert len(versions) == 2
        assert versions[0].version_number == 2
        assert versions[0].is_current is True
        assert versions[1].version_number == 1
        assert versions[1].is_current is False


@pytest.mark.asyncio
async def test_create_new_version_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /api/v1/documents/{id}/versions with non-existent document."""
    from uuid import uuid4

    non_existent_id = uuid4()
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}

    response = await client.post(
        f"/api/v1/documents/{non_existent_id}/versions",
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.asyncio
async def test_create_new_version_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test POST /api/v1/documents/{id}/versions without required permission."""
    from uuid import uuid4

    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}

    response = await client.post(
        f"/api/v1/documents/{uuid4()}/versions",
        files=files,
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert "Access denied" in detail or "Permission denied" in detail


@pytest.mark.asyncio
async def test_create_new_version_multiple_sequential(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test creating multiple versions sequentially via API."""
    test_data = await create_test_data()

    # Create a document
    files = {"document": ("v1.pdf", BytesIO(b"version 1"), "application/pdf")}
    data = {
        "name": "Document Sequential Versions",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Upload version 2
    files2 = {"document": ("v2.pdf", BytesIO(b"version 2"), "application/pdf")}
    response2 = await client.post(
        f"/api/v1/documents/{document_id}/versions",
        files=files2,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert response2.status_code == 200
    assert response2.json()["version_number"] == 2

    # Upload version 3
    files3 = {"document": ("v3.pdf", BytesIO(b"version 3"), "application/pdf")}
    response3 = await client.post(
        f"/api/v1/documents/{document_id}/versions",
        files=files3,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert response3.status_code == 200
    assert response3.json()["version_number"] == 3

    # Get all versions to verify
    get_response = await client.get(
        f"/api/v1/documents/{document_id}/versions",
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert get_response.status_code == 200
    versions = get_response.json()
    assert len(versions) == 3
    assert versions[0]["version_number"] == 3
    assert versions[0]["is_current"] is True


@pytest.mark.asyncio
async def test_create_new_version_creates_history_record(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test that creating new version creates document history entry."""
    test_data = await create_test_data()

    # Create a document
    files = {"document": ("v1.pdf", BytesIO(b"version 1"), "application/pdf")}
    data = {
        "name": "Document History Track",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Upload new version
    files2 = {"document": ("v2.pdf", BytesIO(b"version 2"), "application/pdf")}
    await client.post(
        f"/api/v1/documents/{document_id}/versions",
        files=files2,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    # Verify document history entry in database
    from uuid import UUID

    async with default_session_factory() as session:
        from core.models import DocumentHistory

        stmt = (
            select(DocumentHistory)
            .where(DocumentHistory.document_id == UUID(document_id))
            .where(DocumentHistory.action == "New Version")
            .order_by(DocumentHistory.created_at.desc())
        )
        db_result = await session.execute(stmt)
        history_entry = db_result.scalars().first()

        assert history_entry is not None
        assert "New version uploaded" in history_entry.description
        assert "Document History Track" in history_entry.description


@pytest.mark.asyncio
async def test_preview_document_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{id}/preview endpoint."""
    test_data = await create_test_data()

    # Create a document first
    files = {"document": ("test.pdf", BytesIO(b"PDF content"), "application/pdf")}
    data = {
        "name": "Document to Preview",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Preview the document
    response = await client.get(
        f"/api/v1/documents/{document_id}/preview",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == "inline"
    assert response.content == b"PDF content"


@pytest.mark.asyncio
async def test_preview_document_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{id}/preview with non-existent document."""
    from uuid import uuid4

    non_existent_id = uuid4()

    response = await client.get(
        f"/api/v1/documents/{non_existent_id}/preview",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.asyncio
async def test_preview_document_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test GET /api/v1/documents/{id}/preview without required permission."""
    from uuid import uuid4

    response = await client.get(
        f"/api/v1/documents/{uuid4()}/preview",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert "Access denied" in detail or "Permission denied" in detail


@pytest.mark.asyncio
async def test_preview_document_different_file_types(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test preview endpoint returns correct media types for different file types."""
    test_data = await create_test_data()

    # Test PDF
    files = {"document": ("test.pdf", BytesIO(b"PDF content"), "application/pdf")}
    data = {
        "name": "PDF Document",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    pdf_doc_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/documents/{pdf_doc_id}/preview",
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert response.headers["content-type"] == "application/pdf"

    # Test PNG image
    files = {"document": ("test.png", BytesIO(b"PNG image"), "image/png")}
    data["name"] = "PNG Image"

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    png_doc_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/documents/{png_doc_id}/preview",
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert response.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_preview_document_version_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{id}/versions/{version_id}/preview endpoint."""
    test_data = await create_test_data()

    # Create a document
    files = {"document": ("v1.pdf", BytesIO(b"version 1 content"), "application/pdf")}
    data = {
        "name": "Document Version Preview",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Upload new version
    version_files = {
        "document": ("v2.pdf", BytesIO(b"version 2 content"), "application/pdf")
    }
    version_response = await client.post(
        f"/api/v1/documents/{document_id}/versions",
        files=version_files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert version_response.status_code == 200
    version_id = version_response.json()["id"]

    # Preview the specific version
    response = await client.get(
        f"/api/v1/documents/{document_id}/versions/{version_id}/preview",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == "inline"
    assert response.content == b"version 2 content"


@pytest.mark.asyncio
async def test_preview_document_version_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{id}/versions/{version_id}/preview with non-existent version."""
    from uuid import uuid4

    non_existent_doc_id = uuid4()
    non_existent_version_id = uuid4()

    response = await client.get(
        f"/api/v1/documents/{non_existent_doc_id}/versions/{non_existent_version_id}/preview",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_preview_document_version_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test GET /api/v1/documents/{id}/versions/{version_id}/preview without permission."""
    from uuid import uuid4

    response = await client.get(
        f"/api/v1/documents/{uuid4()}/versions/{uuid4()}/preview",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert "Access denied" in detail or "Permission denied" in detail


@pytest.mark.asyncio
async def test_preview_vs_download_headers(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test that preview and download endpoints have different Content-Disposition headers."""
    test_data = await create_test_data()

    # Create a document
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Preview vs Download Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    document_id = create_response.json()["id"]

    # Preview should have "inline" disposition
    preview_response = await client.get(
        f"/api/v1/documents/{document_id}/preview",
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert preview_response.status_code == 200
    assert preview_response.headers["content-disposition"] == "inline"

    # Download should have "attachment" disposition (or octet-stream media type)
    download_response = await client.get(
        f"/api/v1/documents/{document_id}/download",
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/octet-stream"


@pytest.mark.asyncio
async def test_archive_document_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test PATCH /api/v1/documents/{id}/archive archives document."""
    from db import default_session_factory

    test_data = await create_test_data()

    # Create a document first
    files = {
        "document": ("archive_test.pdf", BytesIO(b"archive content"), "application/pdf")
    }
    data = {
        "name": "Document to Archive API",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "Testing archive endpoint",
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Verify document is not archived initially
    assert create_response.json()["archive"] is False

    # Archive the document
    archive_response = await client.patch(
        f"/api/v1/documents/{document_id}/archive",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert archive_response.status_code == 200
    archive_data = archive_response.json()
    assert archive_data["id"] == document_id
    assert archive_data["archive"] is True

    # Verify in database
    from uuid import UUID

    async with default_session_factory() as session:
        stmt = select(Document).where(Document.id == UUID(document_id))
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()
        assert db_document is not None
        assert db_document.archive is True


@pytest.mark.asyncio
async def test_archive_document_toggle(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test PATCH /api/v1/documents/{id}/archive toggles archive status."""
    from uuid import UUID

    from db import default_session_factory

    test_data = await create_test_data()

    # Create a document
    files = {
        "document": (
            "toggle_archive_api.pdf",
            BytesIO(b"toggle content"),
            "application/pdf",
        )
    }
    data = {
        "name": "Document to Toggle Archive API",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Archive the document (first toggle)
    archive_response1 = await client.patch(
        f"/api/v1/documents/{document_id}/archive",
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert archive_response1.status_code == 200
    assert archive_response1.json()["archive"] is True

    # Verify in database
    async with default_session_factory() as session:
        stmt = select(Document).where(Document.id == UUID(document_id))
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()
        assert db_document.archive is True

    # Unarchive the document (second toggle)
    archive_response2 = await client.patch(
        f"/api/v1/documents/{document_id}/archive",
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert archive_response2.status_code == 200
    assert archive_response2.json()["archive"] is False

    # Verify in database
    async with default_session_factory() as session:
        stmt = select(Document).where(Document.id == UUID(document_id))
        db_result = await session.execute(stmt)
        db_document = db_result.scalar_one_or_none()
        assert db_document.archive is False

    # Archive again (third toggle)
    archive_response3 = await client.patch(
        f"/api/v1/documents/{document_id}/archive",
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert archive_response3.status_code == 200
    assert archive_response3.json()["archive"] is True


@pytest.mark.asyncio
async def test_archive_document_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test PATCH /api/v1/documents/{id}/archive with non-existent document."""
    from uuid import uuid4

    non_existent_id = str(uuid4())

    response = await client.patch(
        f"/api/v1/documents/{non_existent_id}/archive",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.asyncio
async def test_archive_document_unauthorized(client: AsyncClient):
    """Test PATCH /api/v1/documents/{id}/archive without authentication."""
    from uuid import uuid4

    document_id = str(uuid4())

    response = await client.patch(f"/api/v1/documents/{document_id}/archive")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_archive_document_creates_history_entry(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test that archiving creates a document history entry."""
    from core.models import DocumentHistory
    from db import default_session_factory

    test_data = await create_test_data()

    # Create a document
    files = {
        "document": (
            "history_archive.pdf",
            BytesIO(b"archive history"),
            "application/pdf",
        )
    }
    data = {
        "name": "Document Archive History API",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Archive the document
    await client.patch(
        f"/api/v1/documents/{document_id}/archive",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    # Verify document history entry created in database
    from uuid import UUID

    async with default_session_factory() as session:
        stmt = (
            select(DocumentHistory)
            .where(DocumentHistory.document_id == UUID(document_id))
            .where(DocumentHistory.action == "Document Archive")
            .order_by(DocumentHistory.created_at.desc())
        )
        db_result = await session.execute(stmt)
        history_entry = db_result.scalars().first()

        assert history_entry is not None
        assert "archived" in history_entry.description.lower()
        assert "Document Archive History API" in history_entry.description


@pytest.mark.asyncio
async def test_get_documents_excludes_archived_by_default_integration(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents excludes archived documents by default."""

    test_data = await create_test_data()

    # Create non-archived documents
    non_archived_ids = []
    for i in range(3):
        files = {
            "document": (
                f"non_archived_{i}.pdf",
                BytesIO(b"non-archived content"),
                "application/pdf",
            )
        }
        data = {
            "name": f"Non-Archived API {i}",
            "category_id": test_data["category_id"],
            "subcategory_id": test_data["subcategory_id"],
            "stage_id": test_data["stage_id"],
            "assigned_to": test_data["user_id"],
        }
        response = await client.post(
            "/api/v1/documents",
            data=data,
            files=files,
            headers={"X-Session-Key": user_with_documents_permissions},
        )
        assert response.status_code == 200
        non_archived_ids.append(response.json()["id"])

    # Create and archive documents
    archived_ids = []
    for i in range(2):
        files = {
            "document": (
                f"archived_{i}.pdf",
                BytesIO(b"archived content"),
                "application/pdf",
            )
        }
        data = {
            "name": f"Archived API {i}",
            "category_id": test_data["category_id"],
            "subcategory_id": test_data["subcategory_id"],
            "stage_id": test_data["stage_id"],
            "assigned_to": test_data["user_id"],
        }
        response = await client.post(
            "/api/v1/documents",
            data=data,
            files=files,
            headers={"X-Session-Key": user_with_documents_permissions},
        )
        assert response.status_code == 200
        document_id = response.json()["id"]
        archived_ids.append(document_id)

        # Archive the document
        await client.patch(
            f"/api/v1/documents/{document_id}/archive",
            headers={"X-Session-Key": user_with_documents_permissions},
        )

    # Get documents without archive parameter (should default to False)
    response = await client.get(
        "/api/v1/documents",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify all returned documents are not archived
    assert all(doc["archive"] is False for doc in data["data"])
    # Verify archived documents are not in the results
    result_ids = [doc["id"] for doc in data["data"]]
    for archived_id in archived_ids:
        assert archived_id not in result_ids

    # Verify our non-archived documents are in the results
    for non_archived_id in non_archived_ids:
        assert non_archived_id in result_ids


@pytest.mark.asyncio
async def test_get_documents_with_archive_true_integration(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents with archive=true returns only archived documents."""

    test_data = await create_test_data()

    # Create non-archived documents
    for i in range(2):
        files = {
            "document": (
                f"non_archived_{i}.pdf",
                BytesIO(b"non-archived content"),
                "application/pdf",
            )
        }
        data = {
            "name": f"Non-Archived Filter {i}",
            "category_id": test_data["category_id"],
            "subcategory_id": test_data["subcategory_id"],
            "stage_id": test_data["stage_id"],
            "assigned_to": test_data["user_id"],
        }
        response = await client.post(
            "/api/v1/documents",
            data=data,
            files=files,
            headers={"X-Session-Key": user_with_documents_permissions},
        )
        assert response.status_code == 200

    # Create and archive documents
    archived_ids = []
    for i in range(3):
        files = {
            "document": (
                f"archived_{i}.pdf",
                BytesIO(b"archived content"),
                "application/pdf",
            )
        }
        data = {
            "name": f"Archived Filter {i}",
            "category_id": test_data["category_id"],
            "subcategory_id": test_data["subcategory_id"],
            "stage_id": test_data["stage_id"],
            "assigned_to": test_data["user_id"],
        }
        response = await client.post(
            "/api/v1/documents",
            data=data,
            files=files,
            headers={"X-Session-Key": user_with_documents_permissions},
        )
        assert response.status_code == 200
        document_id = response.json()["id"]
        archived_ids.append(document_id)

        # Archive the document
        await client.patch(
            f"/api/v1/documents/{document_id}/archive",
            headers={"X-Session-Key": user_with_documents_permissions},
        )

    # Get only archived documents
    response = await client.get(
        "/api/v1/documents?archive=true",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify all returned documents are archived
    assert all(doc["archive"] is True for doc in data["data"])
    # Verify our archived documents are in the results
    result_ids = [doc["id"] for doc in data["data"]]
    for archived_id in archived_ids:
        assert archived_id in result_ids


@pytest.mark.asyncio
async def test_get_documents_archive_filter_with_category_integration(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test that archive filter works with category filter via API."""
    from configuration.models import Category, Subcategory
    from db import default_session_factory

    test_data = await create_test_data()

    # Create a second category
    async with default_session_factory() as session:
        category2 = Category(title="Second Category API")
        session.add(category2)
        await session.flush()

        subcategory2 = Subcategory(
            title="Second Subcategory API", category_id=category2.id
        )
        session.add(subcategory2)
        await session.commit()
        await session.refresh(category2)
        await session.refresh(subcategory2)
        category2_id = str(category2.id)
        subcategory2_id = str(subcategory2.id)

    # Create non-archived documents in first category
    for i in range(2):
        files = {
            "document": (
                f"cat1_non_archived_{i}.pdf",
                BytesIO(b"content"),
                "application/pdf",
            )
        }
        data = {
            "name": f"Cat1 Non-Archived {i}",
            "category_id": test_data["category_id"],
            "subcategory_id": test_data["subcategory_id"],
            "stage_id": test_data["stage_id"],
            "assigned_to": test_data["user_id"],
        }
        response = await client.post(
            "/api/v1/documents",
            data=data,
            files=files,
            headers={"X-Session-Key": user_with_documents_permissions},
        )
        assert response.status_code == 200

    # Create archived documents in first category
    archived_cat1_ids = []
    for i in range(2):
        files = {
            "document": (
                f"cat1_archived_{i}.pdf",
                BytesIO(b"content"),
                "application/pdf",
            )
        }
        data = {
            "name": f"Cat1 Archived {i}",
            "category_id": test_data["category_id"],
            "subcategory_id": test_data["subcategory_id"],
            "stage_id": test_data["stage_id"],
            "assigned_to": test_data["user_id"],
        }
        response = await client.post(
            "/api/v1/documents",
            data=data,
            files=files,
            headers={"X-Session-Key": user_with_documents_permissions},
        )
        assert response.status_code == 200
        document_id = response.json()["id"]
        archived_cat1_ids.append(document_id)

        # Archive the document
        await client.patch(
            f"/api/v1/documents/{document_id}/archive",
            headers={"X-Session-Key": user_with_documents_permissions},
        )

    # Create archived documents in second category
    for i in range(2):
        files = {
            "document": (
                f"cat2_archived_{i}.pdf",
                BytesIO(b"content"),
                "application/pdf",
            )
        }
        data = {
            "name": f"Cat2 Archived {i}",
            "category_id": category2_id,
            "subcategory_id": subcategory2_id,
            "stage_id": test_data["stage_id"],
            "assigned_to": test_data["user_id"],
        }
        response = await client.post(
            "/api/v1/documents",
            data=data,
            files=files,
            headers={"X-Session-Key": user_with_documents_permissions},
        )
        assert response.status_code == 200
        document_id = response.json()["id"]

        # Archive the document
        await client.patch(
            f"/api/v1/documents/{document_id}/archive",
            headers={"X-Session-Key": user_with_documents_permissions},
        )

    # Get archived documents from first category only
    response = await client.get(
        f"/api/v1/documents?category_id={test_data['category_id']}&archive=true",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify all returned documents are archived and from first category
    assert all(doc["archive"] is True for doc in data["data"])
    assert all(doc["category_id"] == test_data["category_id"] for doc in data["data"])
    # Verify our archived documents from cat1 are in the results
    result_ids = [doc["id"] for doc in data["data"]]
    for archived_id in archived_cat1_ids:
        assert archived_id in result_ids


@pytest.mark.asyncio
async def test_create_comment_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /api/v1/documents/{document_id}/comments creates comment."""
    from core.models import DocumentComment

    test_data = await create_test_data()

    # Create a document first
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document for Comment API Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "API test",
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Create a comment
    comment_data = {"comment": "This is an API integration test comment"}
    response = await client.post(
        f"/api/v1/documents/{document_id}/comments",
        json=comment_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    comment_response = response.json()

    assert comment_response["comment"] == "This is an API integration test comment"
    assert comment_response["document_id"] == document_id
    assert comment_response["id"] is not None
    assert comment_response["user"] is not None
    assert comment_response["created_at"] is not None

    # Verify comment exists in database
    async with default_session_factory() as session:
        from uuid import UUID

        stmt = select(DocumentComment).where(
            DocumentComment.id == UUID(comment_response["id"])
        )
        db_result = await session.execute(stmt)
        db_comment = db_result.scalar_one_or_none()

        assert db_comment is not None
        assert db_comment.comment == "This is an API integration test comment"
        assert str(db_comment.document_id) == document_id


@pytest.mark.asyncio
async def test_create_comment_document_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /api/v1/documents/{document_id}/comments returns 404 for non-existent document."""
    from uuid import uuid4

    non_existent_id = str(uuid4())
    comment_data = {"comment": "Test comment"}

    response = await client.post(
        f"/api/v1/documents/{non_existent_id}/comments",
        json=comment_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_comment_empty_comment_fails(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /api/v1/documents/{document_id}/comments fails with empty comment."""
    test_data = await create_test_data()

    # Create a document first
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document for Empty Comment Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Try to create comment with empty string
    comment_data = {"comment": ""}
    response = await client.post(
        f"/api/v1/documents/{document_id}/comments",
        json=comment_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_multiple_comments_on_same_document_api(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test creating multiple comments on the same document via API."""
    from core.models import DocumentComment

    test_data = await create_test_data()

    # Create a document first
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document for Multiple Comments API",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Create first comment
    comment1_data = {"comment": "First API comment"}
    response1 = await client.post(
        f"/api/v1/documents/{document_id}/comments",
        json=comment1_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response1.status_code == 200
    comment1_id = response1.json()["id"]

    # Create second comment
    comment2_data = {"comment": "Second API comment"}
    response2 = await client.post(
        f"/api/v1/documents/{document_id}/comments",
        json=comment2_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response2.status_code == 200
    comment2_id = response2.json()["id"]

    # Verify both comments have different IDs
    assert comment1_id != comment2_id

    # Verify both comments exist in database
    async with default_session_factory() as session:
        from uuid import UUID

        stmt = select(DocumentComment).where(
            DocumentComment.document_id == UUID(document_id)
        )
        db_result = await session.execute(stmt)
        comments = list(db_result.scalars().all())

        assert len(comments) == 2
        comment_texts = [c.comment for c in comments]
        assert "First API comment" in comment_texts
        assert "Second API comment" in comment_texts


@pytest.mark.asyncio
async def test_create_comment_long_text_api(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test creating a comment with long text via API."""
    from core.models import DocumentComment

    test_data = await create_test_data()

    # Create a document first
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document for Long Comment API",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Create a long comment
    long_comment = "This is a very long comment. " * 100
    comment_data = {"comment": long_comment}
    response = await client.post(
        f"/api/v1/documents/{document_id}/comments",
        json=comment_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    comment_response = response.json()
    comment_id = comment_response["id"]

    assert comment_response["comment"] == long_comment

    # Verify in database
    async with default_session_factory() as session:
        from uuid import UUID

        stmt = select(DocumentComment).where(DocumentComment.id == UUID(comment_id))
        db_result = await session.execute(stmt)
        db_comment = db_result.scalar_one_or_none()

        assert db_comment is not None
        assert db_comment.comment == long_comment
        assert len(db_comment.comment) == len(long_comment)


@pytest.mark.asyncio
async def test_create_comment_requires_permission(client: AsyncClient):
    """Test that creating a comment requires proper permission."""
    from uuid import uuid4

    # Try to create comment without authentication
    document_id = str(uuid4())
    comment_data = {"comment": "Test comment"}

    response = await client.post(
        f"/api/v1/documents/{document_id}/comments",
        json=comment_data,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_document_comments_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{document_id}/comments returns comments."""
    test_data = await create_test_data()

    # Create document
    files = {"document": ("test.pdf", BytesIO(b"test pdf content"), "application/pdf")}
    data = {
        "name": "Document for Get Comments API Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "Test document",
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Create multiple comments
    for i in range(3):
        comment_data = {"comment": f"Comment {i + 1}"}
        comment_response = await client.post(
            f"/api/v1/documents/{document_id}/comments",
            json=comment_data,
            headers={"X-Session-Key": user_with_documents_permissions},
        )
        assert comment_response.status_code == 200

    # Get comments
    response = await client.get(
        f"/api/v1/documents/{document_id}/comments",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    comments = response.json()

    # Verify comments structure
    assert isinstance(comments, list)
    assert len(comments) == 3

    # Verify comments are ordered by created_at ascending (oldest first)
    assert comments[0]["comment"] == "Comment 1"
    assert comments[1]["comment"] == "Comment 2"
    assert comments[2]["comment"] == "Comment 3"

    # Verify all comments have correct structure
    for comment in comments:
        assert comment["id"] is not None
        assert comment["document_id"] == document_id
        assert comment["user"] is not None
        assert comment["created_at"] is not None
        assert "comment" in comment


@pytest.mark.asyncio
async def test_get_document_comments_empty(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{document_id}/comments with no comments."""
    test_data = await create_test_data()

    # Create document without comments
    files = {"document": ("test.pdf", BytesIO(b"test pdf content"), "application/pdf")}
    data = {
        "name": "Document No Comments API",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "Test document",
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Get comments (should be empty)
    response = await client.get(
        f"/api/v1/documents/{document_id}/comments",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    comments = response.json()

    # Should return empty list
    assert isinstance(comments, list)
    assert len(comments) == 0


@pytest.mark.asyncio
async def test_get_document_comments_document_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{document_id}/comments with non-existent document."""
    from uuid import uuid4

    non_existent_id = str(uuid4())

    response = await client.get(
        f"/api/v1/documents/{non_existent_id}/comments",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.asyncio
async def test_get_document_comments_requires_permission(client: AsyncClient):
    """Test that getting comments requires proper permission."""
    from uuid import uuid4

    # Try to get comments without authentication
    document_id = str(uuid4())

    response = await client.get(f"/api/v1/documents/{document_id}/comments")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_document_comments_ordering(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test that comments are returned in created_at ascending order."""

    test_data = await create_test_data()

    # Create document
    files = {"document": ("test.pdf", BytesIO(b"test pdf content"), "application/pdf")}
    data = {
        "name": "Document Comment Ordering API Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "Test document",
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Create multiple comments with small delays
    for i in range(5):
        comment_data = {"comment": f"Ordered Comment {i}"}
        comment_response = await client.post(
            f"/api/v1/documents/{document_id}/comments",
            json=comment_data,
            headers={"X-Session-Key": user_with_documents_permissions},
        )
        assert comment_response.status_code == 200
        # Small delay to ensure different timestamps
        await asyncio.sleep(0.01)

    # Get comments
    response = await client.get(
        f"/api/v1/documents/{document_id}/comments",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    comments = response.json()

    # Verify comments are in ascending order
    assert len(comments) == 5
    for i in range(5):
        assert comments[i]["comment"] == f"Ordered Comment {i}"

    # Verify timestamps are in ascending order
    from datetime import datetime

    for i in range(len(comments) - 1):
        timestamp1 = datetime.fromisoformat(
            comments[i]["created_at"].replace("Z", "+00:00")
        )
        timestamp2 = datetime.fromisoformat(
            comments[i + 1]["created_at"].replace("Z", "+00:00")
        )
        assert timestamp1 <= timestamp2


@pytest.mark.asyncio
async def test_share_document_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /api/v1/documents/{document_id}/share shares document."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User
    from db import default_session_factory

    test_data = await create_test_data()

    # Create additional users to share with
    async with default_session_factory() as session:
        user1 = User(
            first_name="Share",
            last_name="User1",
            username="share_user1_api_test",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        user2 = User(
            first_name="Share",
            last_name="User2",
            username="share_user2_api_test",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add_all([user1, user2])
        await session.commit()
        await session.refresh(user1)
        await session.refresh(user2)
        user1_id = str(user1.id)
        user2_id = str(user2.id)

    # Create a document first
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document to Share API Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "Test document for sharing",
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Share the document
    share_data = {
        "user_ids": [user1_id, user2_id],
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
    }

    response = await client.post(
        f"/api/v1/documents/{document_id}/share",
        json=share_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    shares = response.json()

    # Verify shares created
    assert len(shares) == 2
    assert all(share["document_id"] == document_id for share in shares)
    shared_user_ids = [share["user_id"] for share in shares]
    assert user1_id in shared_user_ids
    assert user2_id in shared_user_ids
    assert all(share["start_date"] == "2024-01-01" for share in shares)
    assert all(share["end_date"] == "2024-12-31" for share in shares)

    # Verify shares persisted in database
    async with default_session_factory() as session:
        from uuid import UUID

        from core.models import ShareDocument

        result = await session.execute(
            select(ShareDocument).where(ShareDocument.document_id == UUID(document_id))
        )
        db_shares = list(result.scalars().all())
        assert len(db_shares) == 2


@pytest.mark.asyncio
async def test_share_document_without_dates(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test sharing document without start and end dates."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User
    from db import default_session_factory

    test_data = await create_test_data()

    # Create user to share with
    async with default_session_factory() as session:
        user = User(
            first_name="Share",
            last_name="User",
            username="share_user_no_dates_api_test",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = str(user.id)

    # Create a document first
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document to Share Without Dates API Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "Test document for sharing without dates",
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Share the document without dates
    share_data = {"user_ids": [user_id]}

    response = await client.post(
        f"/api/v1/documents/{document_id}/share",
        json=share_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    shares = response.json()

    # Verify share created without dates
    assert len(shares) == 1
    assert shares[0]["start_date"] is None
    assert shares[0]["end_date"] is None


@pytest.mark.asyncio
async def test_share_document_invalid_date_range(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test sharing document with invalid date range fails."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User
    from db import default_session_factory

    test_data = await create_test_data()

    # Create user to share with
    async with default_session_factory() as session:
        user = User(
            first_name="Share",
            last_name="User",
            username="share_user_invalid_dates_api_test",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = str(user.id)

    # Create a document first
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document Invalid Date Range API Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "Test document",
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Try to share with end date before start date
    share_data = {
        "user_ids": [user_id],
        "start_date": "2024-12-31",
        "end_date": "2024-01-01",
    }

    response = await client.post(
        f"/api/v1/documents/{document_id}/share",
        json=share_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 400
    error = response.json()
    assert "start date must be before end date" in error["detail"].lower()


@pytest.mark.asyncio
async def test_share_document_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test sharing non-existent document fails."""
    from uuid import uuid4

    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User
    from db import default_session_factory

    # Create user to share with
    async with default_session_factory() as session:
        user = User(
            first_name="Share",
            last_name="User",
            username="share_user_not_found_api_test",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = str(user.id)

    non_existent_id = str(uuid4())
    share_data = {"user_ids": [user_id]}

    response = await client.post(
        f"/api/v1/documents/{non_existent_id}/share",
        json=share_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404
    error = response.json()
    assert "document not found" in error["detail"].lower()


@pytest.mark.asyncio
async def test_share_document_user_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test sharing document with non-existent user fails."""
    from uuid import uuid4

    test_data = await create_test_data()

    # Create a document first
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document User Not Found API Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "Test document",
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Try to share with non-existent user
    non_existent_user = str(uuid4())
    share_data = {"user_ids": [non_existent_user]}

    response = await client.post(
        f"/api/v1/documents/{document_id}/share",
        json=share_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404
    error = response.json()
    assert "user not found" in error["detail"].lower()


@pytest.mark.asyncio
async def test_get_shared_users_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{document_id}/shared-users returns shared users."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User
    from db import default_session_factory

    test_data = await create_test_data()

    # Create users to share with
    async with default_session_factory() as session:
        user1 = User(
            first_name="Share",
            last_name="User1",
            username="get_shared_user1_api_test",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        user2 = User(
            first_name="Share",
            last_name="User2",
            username="get_shared_user2_api_test",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add_all([user1, user2])
        await session.commit()
        await session.refresh(user1)
        await session.refresh(user2)
        user1_id = str(user1.id)
        user2_id = str(user2.id)

    # Create a document
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document Get Shared Users API Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "Test document",
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Share the document
    share_data = {"user_ids": [user1_id, user2_id]}

    share_response = await client.post(
        f"/api/v1/documents/{document_id}/share",
        json=share_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert share_response.status_code == 200

    # Get shared users
    response = await client.get(
        f"/api/v1/documents/{document_id}/shared-users",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    shares = response.json()

    # Verify
    assert len(shares) == 2
    assert all(share["document_id"] == document_id for share in shares)
    shared_user_ids = [share["user_id"] for share in shares]
    assert user1_id in shared_user_ids
    assert user2_id in shared_user_ids


@pytest.mark.asyncio
async def test_get_shared_users_empty(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{document_id}/shared-users returns empty list when no shares."""
    test_data = await create_test_data()

    # Create a document without sharing
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document No Shares API Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
        "description": "Test document",
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Get shared users (should be empty)
    response = await client.get(
        f"/api/v1/documents/{document_id}/shared-users",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    shares = response.json()

    # Should return empty list
    assert isinstance(shares, list)
    assert len(shares) == 0


@pytest.mark.asyncio
async def test_get_shared_users_document_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test GET /api/v1/documents/{document_id}/shared-users fails for non-existent document."""
    from uuid import uuid4

    non_existent_id = str(uuid4())

    response = await client.get(
        f"/api/v1/documents/{non_existent_id}/shared-users",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404
    error = response.json()
    assert "document not found" in error["detail"].lower()


@pytest.mark.asyncio
async def test_delete_share_document_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test DELETE /api/v1/documents/{document_id}/share/{share_id} removes share."""
    from uuid import UUID

    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User
    from core.models import ShareDocument
    from db import default_session_factory

    test_data = await create_test_data()

    # Create user to share with
    async with default_session_factory() as session:
        user = User(
            first_name="Share",
            last_name="User",
            username="share_user_delete_api_test",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = str(user.id)

    # Create a document
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "API Delete Share Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Share the document
    share_data = {"user_ids": [user_id]}
    share_response = await client.post(
        f"/api/v1/documents/{document_id}/share",
        json=share_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert share_response.status_code == 200
    shares = share_response.json()
    assert len(shares) == 1
    share_id = shares[0]["id"]

    # Verify share exists in database
    async with default_session_factory() as session:
        stmt = select(ShareDocument).where(ShareDocument.id == UUID(share_id))
        db_result = await session.execute(stmt)
        db_share = db_result.scalar_one_or_none()
        assert db_share is not None

    # Delete the share
    response = await client.delete(
        f"/api/v1/documents/{document_id}/share/{share_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["detail"] == "Assigned document successfully removed!"

    # Verify share was removed from database
    async with default_session_factory() as session:
        stmt = select(ShareDocument).where(ShareDocument.id == UUID(share_id))
        db_result = await session.execute(stmt)
        db_share = db_result.scalar_one_or_none()
        assert db_share is None


@pytest.mark.asyncio
async def test_delete_share_document_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test DELETE /api/v1/documents/{document_id}/share/{share_id} with non-existent share fails."""
    from uuid import uuid4

    test_data = await create_test_data()

    # Create a document
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "API Delete Share Not Found Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Try to delete non-existent share
    non_existent_share_id = str(uuid4())
    response = await client.delete(
        f"/api/v1/documents/{document_id}/share/{non_existent_share_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404
    error = response.json()
    assert "share not found" in error["detail"].lower()


@pytest.mark.asyncio
async def test_delete_share_document_document_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test DELETE /api/v1/documents/{document_id}/share/{share_id} with non-existent document fails."""
    from uuid import uuid4

    non_existent_doc_id = str(uuid4())
    share_id = str(uuid4())

    response = await client.delete(
        f"/api/v1/documents/{non_existent_doc_id}/share/{share_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404
    error = response.json()
    assert "document not found" in error["detail"].lower()


@pytest.mark.asyncio
async def test_delete_share_document_wrong_document(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test DELETE /api/v1/documents/{document_id}/share/{share_id} with mismatched document ID fails."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User
    from db import default_session_factory

    test_data = await create_test_data()

    # Create user to share with
    async with default_session_factory() as session:
        user = User(
            first_name="Share",
            last_name="User",
            username="share_user_wrong_doc_api_test",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = str(user.id)

    # Create first document
    files1 = {"document": ("test1.pdf", BytesIO(b"test content 1"), "application/pdf")}
    data1 = {
        "name": "API Wrong Doc Test 1",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response1 = await client.post(
        "/api/v1/documents",
        data=data1,
        files=files1,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response1.status_code == 200
    document_id1 = create_response1.json()["id"]

    # Create second document
    files2 = {"document": ("test2.pdf", BytesIO(b"test content 2"), "application/pdf")}
    data2 = {
        "name": "API Wrong Doc Test 2",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response2 = await client.post(
        "/api/v1/documents",
        data=data2,
        files=files2,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response2.status_code == 200
    document_id2 = create_response2.json()["id"]

    # Share document 1
    share_data = {"user_ids": [user_id]}
    share_response = await client.post(
        f"/api/v1/documents/{document_id1}/share",
        json=share_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert share_response.status_code == 200
    shares = share_response.json()
    share_id = shares[0]["id"]

    # Try to delete share using wrong document ID
    response = await client.delete(
        f"/api/v1/documents/{document_id2}/share/{share_id}",  # Wrong document ID
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 400
    error = response.json()
    assert "does not belong to this document" in error["detail"].lower()


@pytest.mark.asyncio
async def test_generate_share_link_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /api/v1/documents/{id}/share-link generates encrypted share link."""
    from datetime import date, timedelta

    test_data = await create_test_data()

    # Create a document
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document for Share Link",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Generate share link
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_data = {"expiration_date": future_date, "password": "test123"}

    response = await client.post(
        f"/api/v1/documents/{document_id}/share-link",
        json=share_link_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    result = response.json()
    assert "token" in result
    assert isinstance(result["token"], str)
    assert len(result["token"]) > 0


@pytest.mark.asyncio
async def test_generate_share_link_without_password(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /api/v1/documents/{id}/share-link without password."""
    from datetime import date, timedelta

    test_data = await create_test_data()

    # Create a document
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document for Share Link No Pass",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Generate share link without password
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_data = {"expiration_date": future_date, "password": None}

    response = await client.post(
        f"/api/v1/documents/{document_id}/share-link",
        json=share_link_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 200
    result = response.json()
    assert "token" in result
    assert isinstance(result["token"], str)


@pytest.mark.asyncio
async def test_generate_share_link_expired_date_fails(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /api/v1/documents/{id}/share-link with past date fails."""
    from datetime import date, timedelta

    test_data = await create_test_data()

    # Create a document
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document for Expired Link",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Try to generate share link with past date
    past_date = (date.today() - timedelta(days=1)).isoformat()
    share_link_data = {"expiration_date": past_date, "password": None}

    response = await client.post(
        f"/api/v1/documents/{document_id}/share-link",
        json=share_link_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 400
    error = response.json()
    assert "future" in error["detail"].lower()


@pytest.mark.asyncio
async def test_generate_share_link_document_not_found(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /api/v1/documents/{id}/share-link with non-existent document."""
    from datetime import date, timedelta
    from uuid import uuid4

    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_data = {"expiration_date": future_date, "password": None}

    response = await client.post(
        f"/api/v1/documents/{uuid4()}/share-link",
        json=share_link_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert response.status_code == 404
    error = response.json()
    assert "document not found" in error["detail"].lower()


@pytest.mark.asyncio
async def test_preview_shared_document_success(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /documents/shared/{token} successfully accesses shared document."""
    from datetime import date, timedelta

    test_data = await create_test_data()

    # Create a document
    files = {"document": ("test.pdf", BytesIO(b"PDF test content"), "application/pdf")}
    data = {
        "name": "Document for Preview",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Generate share link with password
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_data = {"expiration_date": future_date, "password": "secret123"}

    link_response = await client.post(
        f"/api/v1/documents/{document_id}/share-link",
        json=share_link_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert link_response.status_code == 200
    token = link_response.json()["token"]

    # Access shared document with correct password (no authentication required)
    access_data = {"password": "secret123"}
    response = await client.post(
        f"/api/v1/documents/shared/{token}",
        json=access_data,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "inline" in response.headers.get("content-disposition", "").lower()
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_preview_shared_document_without_password(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /documents/shared/{token} with no password protection."""
    from datetime import date, timedelta

    test_data = await create_test_data()

    # Create a document
    files = {"document": ("test.pdf", BytesIO(b"PDF test content"), "application/pdf")}
    data = {
        "name": "Document for Preview No Pass",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Generate share link without password
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_data = {"expiration_date": future_date, "password": None}

    link_response = await client.post(
        f"/api/v1/documents/{document_id}/share-link",
        json=share_link_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert link_response.status_code == 200
    token = link_response.json()["token"]

    # Access shared document without password (no authentication required)
    access_data = {"password": None}
    response = await client.post(
        f"/api/v1/documents/shared/{token}",
        json=access_data,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_preview_shared_document_wrong_password(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /documents/shared/{token} with wrong password fails."""
    from datetime import date, timedelta

    test_data = await create_test_data()

    # Create a document
    files = {"document": ("test.pdf", BytesIO(b"PDF test content"), "application/pdf")}
    data = {
        "name": "Document for Wrong Password Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Generate share link with password
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_data = {"expiration_date": future_date, "password": "correct_password"}

    link_response = await client.post(
        f"/api/v1/documents/{document_id}/share-link",
        json=share_link_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert link_response.status_code == 200
    token = link_response.json()["token"]

    # Try to access with wrong password
    access_data = {"password": "wrong_password"}
    response = await client.post(
        f"/api/v1/documents/shared/{token}",
        json=access_data,
    )

    assert response.status_code == 401
    error = response.json()
    assert "password" in error["detail"].lower()


@pytest.mark.asyncio
async def test_preview_shared_document_missing_password(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test POST /documents/shared/{token} with missing required password fails."""
    from datetime import date, timedelta

    test_data = await create_test_data()

    # Create a document
    files = {"document": ("test.pdf", BytesIO(b"PDF test content"), "application/pdf")}
    data = {
        "name": "Document for Missing Password Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Generate share link with password
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_data = {"expiration_date": future_date, "password": "required_password"}

    link_response = await client.post(
        f"/api/v1/documents/{document_id}/share-link",
        json=share_link_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert link_response.status_code == 200
    token = link_response.json()["token"]

    # Try to access without providing password
    access_data = {"password": None}
    response = await client.post(
        f"/api/v1/documents/shared/{token}",
        json=access_data,
    )

    assert response.status_code == 401
    error = response.json()
    assert "password" in error["detail"].lower()


@pytest.mark.asyncio
async def test_preview_shared_document_invalid_token(client: AsyncClient):
    """Test POST /documents/shared/{token} with invalid token fails."""
    access_data = {"password": None}
    response = await client.post(
        "/api/v1/documents/shared/invalid-token",
        json=access_data,
    )

    assert response.status_code == 400
    error = response.json()
    assert "invalid" in error["detail"].lower()


@pytest.mark.asyncio
async def test_share_link_creates_history_entry(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test that generating a share link creates a document history entry."""
    from datetime import date, timedelta

    test_data = await create_test_data()

    # Create a document
    files = {"document": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
    data = {
        "name": "Document for History Test",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Generate share link
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_data = {"expiration_date": future_date, "password": None}

    await client.post(
        f"/api/v1/documents/{document_id}/share-link",
        json=share_link_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    # Check document history
    from core.models import DocumentHistory

    async with default_session_factory() as session:
        from uuid import UUID

        stmt = select(DocumentHistory).where(
            DocumentHistory.document_id == UUID(document_id)
        )
        result = await session.execute(stmt)
        histories = result.scalars().all()

        # Should have at least 2 entries: create + share link generate
        assert len(histories) >= 2

        # Check if there's a share link generate history
        share_link_history = [h for h in histories if "share link" in h.action.lower()]
        assert len(share_link_history) >= 1
        assert "generated" in share_link_history[0].description.lower()


@pytest.mark.asyncio
async def test_preview_shared_document_multiple_times(
    client: AsyncClient, user_with_documents_permissions: str
):
    """Test that a share link can be used multiple times before expiration."""
    from datetime import date, timedelta

    test_data = await create_test_data()

    # Create a document
    files = {"document": ("test.pdf", BytesIO(b"PDF test content"), "application/pdf")}
    data = {
        "name": "Document for Multiple Access",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    create_response = await client.post(
        "/api/v1/documents",
        data=data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response.status_code == 200
    document_id = create_response.json()["id"]

    # Generate share link
    future_date = (date.today() + timedelta(days=30)).isoformat()
    share_link_data = {"expiration_date": future_date, "password": None}

    link_response = await client.post(
        f"/api/v1/documents/{document_id}/share-link",
        json=share_link_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert link_response.status_code == 200
    token = link_response.json()["token"]

    # Access the same link multiple times
    access_data = {"password": None}
    for _ in range(3):
        response = await client.post(
            f"/api/v1/documents/shared/{token}",
            json=access_data,
        )
        assert response.status_code == 200
        assert len(response.content) > 0
