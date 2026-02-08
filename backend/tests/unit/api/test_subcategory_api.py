import os
import sys
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from configuration.categories.fakes import FakeCategoryService
from configuration.models import Category
from configuration.subcategories.api import (
    create_subcategory,
    delete_subcategory,
    get_subcategories,
    get_subcategory,
    update_subcategory,
)
from configuration.subcategories.fakes import FakeSubcategoryService
from configuration.subcategories.schemas import SubcategoryCreate, SubcategoryUpdate


@pytest.fixture
def test_category():
    """Provide a test category for subcategories."""
    return Category(id=uuid4(), title="test category")


@pytest.fixture
def category_service(test_category):
    """Provide a fake category service with test category."""
    service = FakeCategoryService()
    service.categories[test_category.id] = test_category
    return service


@pytest.fixture
def subcategory_service(test_category):
    """Provide a fake subcategory service with test category."""
    service = FakeSubcategoryService()
    service.categories[test_category.id] = test_category
    return service


@pytest.mark.asyncio
async def test_get_subcategories_api(subcategory_service, test_category):
    """Test GET /subcategories endpoint."""
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory 1", category_id=test_category.id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory 2", category_id=test_category.id)
    )

    result = await get_subcategories(
        page=1,
        page_size=10,
        search=None,
        category_id=None,
        subcategory_service=subcategory_service,
    )

    assert result.total_rows == 2
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_get_subcategories_api_with_pagination(
    subcategory_service, test_category
):
    """Test GET /subcategories endpoint with pagination."""
    for i in range(5):
        await subcategory_service.create_subcategory(
            SubcategoryCreate(title=f"Subcategory {i}", category_id=test_category.id)
        )

    result = await get_subcategories(
        page=1,
        page_size=2,
        search=None,
        category_id=None,
        subcategory_service=subcategory_service,
    )

    assert result.total_rows == 5
    assert len(result.data) == 2
    assert result.total_pages == 3
    assert result.has_next is True


@pytest.mark.asyncio
async def test_get_subcategories_api_with_search(subcategory_service, test_category):
    """Test GET /subcategories endpoint with search."""
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Reports", category_id=test_category.id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Approved Reports", category_id=test_category.id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Project", category_id=test_category.id)
    )

    result = await get_subcategories(
        page=1,
        page_size=10,
        search="report",
        category_id=None,
        subcategory_service=subcategory_service,
    )

    assert result.total_rows == 2
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_get_subcategories_api_with_category_filter(
    subcategory_service, test_category
):
    """Test GET /subcategories endpoint with category filter."""
    category_id_2 = uuid4()
    subcategory_service.categories[category_id_2] = None

    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory 1", category_id=test_category.id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory 2", category_id=test_category.id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory 3", category_id=category_id_2)
    )

    result = await get_subcategories(
        page=1,
        page_size=10,
        search=None,
        category_id=test_category.id,
        subcategory_service=subcategory_service,
    )

    assert result.total_rows == 2
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_get_subcategories_api_with_invalid_category(subcategory_service):
    """Test GET /subcategories endpoint with invalid category."""
    with pytest.raises(HTTPException) as exc_info:
        await get_subcategories(
            page=1,
            page_size=10,
            search=None,
            category_id=uuid4(),
            subcategory_service=subcategory_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_subcategory_api_success(subcategory_service, test_category):
    """Test GET /subcategories/{id} endpoint with valid ID."""
    created = await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Test Subcategory", category_id=test_category.id)
    )

    result = await get_subcategory(
        subcategory_id=created.id,
        subcategory_service=subcategory_service,
    )

    assert result.id == created.id
    assert result.title == "test subcategory"


@pytest.mark.asyncio
async def test_get_subcategory_api_not_found(subcategory_service):
    """Test GET /subcategories/{id} endpoint with invalid ID."""
    with pytest.raises(HTTPException) as exc_info:
        await get_subcategory(
            subcategory_id=uuid4(), subcategory_service=subcategory_service
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_subcategory_api_success(subcategory_service, test_category):
    """Test POST /subcategories endpoint."""
    subcategory_data = SubcategoryCreate(
        title="New Subcategory", category_id=test_category.id
    )

    result = await create_subcategory(
        subcategory_create=subcategory_data,
        subcategory_service=subcategory_service,
    )

    assert result.title == "new subcategory"
    assert result.category_id == test_category.id


@pytest.mark.asyncio
async def test_create_subcategory_api_invalid_category(subcategory_service):
    """Test POST /subcategories endpoint with invalid category."""
    subcategory_data = SubcategoryCreate(title="New Subcategory", category_id=uuid4())

    with pytest.raises(HTTPException) as exc_info:
        await create_subcategory(
            subcategory_create=subcategory_data, subcategory_service=subcategory_service
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_subcategory_api_duplicate_title(
    subcategory_service, test_category
):
    """Test POST /subcategories endpoint with duplicate title."""
    subcategory_data = SubcategoryCreate(
        title="Duplicate", category_id=test_category.id
    )

    await subcategory_service.create_subcategory(subcategory_data)

    with pytest.raises(HTTPException) as exc_info:
        await create_subcategory(
            subcategory_create=subcategory_data, subcategory_service=subcategory_service
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_subcategory_api_success(subcategory_service, test_category):
    """Test PUT /subcategories/{id} endpoint."""
    created = await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Original", category_id=test_category.id)
    )

    update_data = SubcategoryUpdate(title="Updated", category_id=test_category.id)
    result = await update_subcategory(
        subcategory_id=created.id,
        subcategory_update=update_data,
        subcategory_service=subcategory_service,
    )

    assert result.id == created.id
    assert result.title == "updated"


@pytest.mark.asyncio
async def test_update_subcategory_api_not_found(subcategory_service, test_category):
    """Test PUT /subcategories/{id} endpoint with invalid ID."""
    update_data = SubcategoryUpdate(title="Updated", category_id=test_category.id)

    with pytest.raises(HTTPException) as exc_info:
        await update_subcategory(
            subcategory_id=uuid4(),
            subcategory_update=update_data,
            subcategory_service=subcategory_service,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_subcategory_api_duplicate_title(
    subcategory_service, test_category
):
    """Test PUT /subcategories/{id} endpoint with duplicate title."""
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory 1", category_id=test_category.id)
    )
    subcategory2 = await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory 2", category_id=test_category.id)
    )

    update_data = SubcategoryUpdate(title="Subcategory 1", category_id=test_category.id)

    with pytest.raises(HTTPException) as exc_info:
        await update_subcategory(
            subcategory_id=subcategory2.id,
            subcategory_update=update_data,
            subcategory_service=subcategory_service,
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_delete_subcategory_api_success(subcategory_service, test_category):
    """Test DELETE /subcategories/{id} endpoint."""
    created = await subcategory_service.create_subcategory(
        SubcategoryCreate(title="To Delete", category_id=test_category.id)
    )

    result = await delete_subcategory(
        subcategory_id=created.id, subcategory_service=subcategory_service
    )

    assert "deleted successfully" in result.detail.lower()


@pytest.mark.asyncio
async def test_delete_subcategory_api_not_found(subcategory_service):
    """Test DELETE /subcategories/{id} endpoint with invalid ID."""
    with pytest.raises(HTTPException) as exc_info:
        await delete_subcategory(
            subcategory_id=uuid4(), subcategory_service=subcategory_service
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_subcategory_api_converts_title_to_lowercase(
    subcategory_service, test_category
):
    """Test POST /subcategories endpoint converts title to lowercase."""
    subcategory_data = SubcategoryCreate(
        title="UPPERCASE TITLE", category_id=test_category.id
    )

    result = await create_subcategory(
        subcategory_create=subcategory_data,
        subcategory_service=subcategory_service,
    )

    assert result.title == "uppercase title"
