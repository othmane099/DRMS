import os
import sys

import pytest
from fastapi import HTTPException
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from configuration.categories.api import (
    create_category,
    delete_category,
    get_categories,
    get_category,
    update_category,
)
from configuration.categories.fakes import FakeCategoryService
from configuration.categories.schemas import CategoryCreate, CategoryUpdate


@pytest.fixture
def category_service():
    """Provide a fake category service."""
    return FakeCategoryService()


@pytest.mark.asyncio
async def test_get_categories_api(category_service):
    """Test GET /categories endpoint."""
    await category_service.create_category(CategoryCreate(title="Category 1"))
    await category_service.create_category(CategoryCreate(title="Category 2"))

    result = await get_categories(
        page=1, page_size=10, search=None, category_service=category_service
    )

    assert result.total_rows == 2
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_get_categories_api_with_pagination(category_service):
    """Test GET /categories endpoint with pagination."""
    for i in range(5):
        await category_service.create_category(CategoryCreate(title=f"Category {i}"))

    result = await get_categories(
        page=1, page_size=2, search=None, category_service=category_service
    )

    assert result.total_rows == 5
    assert len(result.data) == 2
    assert result.total_pages == 3
    assert result.has_next is True


@pytest.mark.asyncio
async def test_get_categories_api_with_search(category_service):
    """Test GET /categories endpoint with search."""
    await category_service.create_category(CategoryCreate(title="Reports"))
    await category_service.create_category(CategoryCreate(title="Approved Reports"))
    await category_service.create_category(CategoryCreate(title="Project"))

    result = await get_categories(
        page=1, page_size=10, search="report", category_service=category_service
    )

    assert result.total_rows == 2
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_get_category_api_success(category_service):
    """Test GET /categories/{id} endpoint with valid ID."""
    created = await category_service.create_category(
        CategoryCreate(title="Test Category")
    )

    result = await get_category(
        category_id=created.id, category_service=category_service
    )

    assert result.id == created.id
    assert result.title == "test category"


@pytest.mark.asyncio
async def test_get_category_api_not_found(category_service):
    """Test GET /categories/{id} endpoint with invalid ID."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await get_category(category_id=uuid4(), category_service=category_service)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_category_api_success(category_service):
    """Test POST /categories endpoint."""
    category_data = CategoryCreate(title="New Category")

    result = await create_category(
        category_create=category_data, category_service=category_service
    )

    assert result.title == "new category"


@pytest.mark.asyncio
async def test_create_category_api_duplicate_title(category_service):
    """Test POST /categories endpoint with duplicate title."""
    category_data = CategoryCreate(title="Duplicate")

    await category_service.create_category(category_data)

    with pytest.raises(HTTPException) as exc_info:
        await create_category(
            category_create=category_data, category_service=category_service
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_category_api_success(category_service):
    """Test PUT /categories/{id} endpoint."""
    created = await category_service.create_category(CategoryCreate(title="Original"))

    update_data = CategoryUpdate(title="Updated")
    result = await update_category(
        category_id=created.id,
        category_update=update_data,
        category_service=category_service,
    )

    assert result.id == created.id
    assert result.title == "updated"


@pytest.mark.asyncio
async def test_update_category_api_not_found(category_service):
    """Test PUT /categories/{id} endpoint with invalid ID."""
    from uuid import uuid4

    update_data = CategoryUpdate(title="Updated")

    with pytest.raises(HTTPException) as exc_info:
        await update_category(
            category_id=uuid4(),
            category_update=update_data,
            category_service=category_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_category_api_duplicate_title(category_service):
    """Test PUT /categories/{id} endpoint with duplicate title."""
    await category_service.create_category(CategoryCreate(title="Category 1"))
    category2 = await category_service.create_category(
        CategoryCreate(title="Category 2")
    )

    update_data = CategoryUpdate(title="Category 1")

    with pytest.raises(HTTPException) as exc_info:
        await update_category(
            category_id=category2.id,
            category_update=update_data,
            category_service=category_service,
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_delete_category_api_success(category_service):
    """Test DELETE /categories/{id} endpoint."""
    created = await category_service.create_category(CategoryCreate(title="To Delete"))

    result = await delete_category(
        category_id=created.id, category_service=category_service
    )

    assert "deleted successfully" in result.detail.lower()


@pytest.mark.asyncio
async def test_delete_category_api_not_found(category_service):
    """Test DELETE /categories/{id} endpoint with invalid ID."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await delete_category(category_id=uuid4(), category_service=category_service)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_category_api_converts_title_to_lowercase(category_service):
    """Test POST /categories endpoint converts title to lowercase."""
    category_data = CategoryCreate(title="UPPERCASE TITLE")

    result = await create_category(
        category_create=category_data, category_service=category_service
    )

    assert result.title == "uppercase title"
