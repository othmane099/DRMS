import os
import sys

import pytest
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from configuration.categories.schemas import CategoryCreate, CategoryUpdate
from configuration.categories.service import CategoryServiceImpl
from schemas import Error, Message
from unit_of_work.fake_uow import FakeUnitOfWork


@pytest.fixture
def uow():
    """Provide a fake unit of work."""
    return FakeUnitOfWork()


@pytest.fixture
def category_service(uow):
    """Provide a category service with fake UoW."""
    return CategoryServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_create_category_success(category_service):
    """Test creating a new category successfully."""
    category_data = CategoryCreate(title="Reports")

    result = await category_service.create_category(category_data)

    assert not isinstance(result, Error)
    assert result.title == "reports"


@pytest.mark.asyncio
async def test_create_category_duplicate_title(category_service):
    """Test creating a category with duplicate title fails."""
    category_data = CategoryCreate(title="Reports")

    await category_service.create_category(category_data)

    result = await category_service.create_category(category_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_create_category_duplicate_title_case_insensitive(category_service):
    """Test creating a category with duplicate title (case insensitive) fails."""
    category_data1 = CategoryCreate(title="Reports")
    category_data2 = CategoryCreate(title="REPORTS")

    await category_service.create_category(category_data1)

    result = await category_service.create_category(category_data2)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_category_by_id_success(category_service):
    """Test retrieving a category by ID."""
    category_data = CategoryCreate(title="Reports")

    created = await category_service.create_category(category_data)
    assert not isinstance(created, Error)

    result = await category_service.get_category_by_id(created.id)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.title == "reports"


@pytest.mark.asyncio
async def test_get_category_by_id_not_found(category_service):
    """Test retrieving a non-existent category returns error."""
    from uuid import uuid4

    result = await category_service.get_category_by_id(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_update_category_success(category_service):
    """Test updating a category successfully."""
    category_data = CategoryCreate(title="Reports")
    created = await category_service.create_category(category_data)
    assert not isinstance(created, Error)

    update_data = CategoryUpdate(title="Final Reports")
    result = await category_service.update_category(created.id, update_data)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.title == "final reports"


@pytest.mark.asyncio
async def test_update_category_not_found(category_service):
    """Test updating a non-existent category returns error."""
    from uuid import uuid4

    update_data = CategoryUpdate(title="Reports")
    result = await category_service.update_category(uuid4(), update_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_update_category_duplicate_title(category_service):
    """Test updating a category with duplicate title fails."""
    category1 = CategoryCreate(title="Category One")
    category2 = CategoryCreate(title="Category Two")

    created1 = await category_service.create_category(category1)
    created2 = await category_service.create_category(category2)
    assert not isinstance(created1, Error)
    assert not isinstance(created2, Error)

    update_data = CategoryUpdate(title="Category One")
    result = await category_service.update_category(created2.id, update_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_update_category_same_title(category_service):
    """Test updating a category with the same title succeeds."""
    category_data = CategoryCreate(title="Reports")
    created = await category_service.create_category(category_data)
    assert not isinstance(created, Error)

    update_data = CategoryUpdate(title="Reports")
    result = await category_service.update_category(created.id, update_data)

    assert not isinstance(result, Error)


@pytest.mark.asyncio
async def test_delete_category_success(category_service):
    """Test deleting a category successfully."""
    category_data = CategoryCreate(title="To Delete")
    created = await category_service.create_category(category_data)
    assert not isinstance(created, Error)

    result = await category_service.delete_category(created.id)

    assert isinstance(result, Message)
    assert "deleted successfully" in result.detail.lower()

    get_result = await category_service.get_category_by_id(created.id)
    assert isinstance(get_result, Error)
    assert get_result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_category_not_found(category_service):
    """Test deleting a non-existent category returns error."""
    from uuid import uuid4

    result = await category_service.delete_category(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_all_categories_paginated(category_service):
    """Test retrieving paginated categories."""
    await category_service.create_category(CategoryCreate(title="Category A"))
    await category_service.create_category(CategoryCreate(title="Category B"))
    await category_service.create_category(CategoryCreate(title="Category C"))

    result = await category_service.get_all_categories_paginated(page=1, page_size=2)

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 3
    assert result.total_pages == 2
    assert result.has_next is True
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_get_all_categories_paginated_with_search(category_service):
    """Test retrieving paginated categories with search."""
    await category_service.create_category(CategoryCreate(title="Reports"))
    await category_service.create_category(CategoryCreate(title="HSE"))
    await category_service.create_category(CategoryCreate(title="Final Reports"))

    result = await category_service.get_all_categories_paginated(
        page=1, page_size=10, search="report"
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 2


@pytest.mark.asyncio
async def test_get_all_categories_includes_subcategory_count(category_service):
    """Test that paginated categories include subcategory_count."""
    await category_service.create_category(CategoryCreate(title="Category A"))
    await category_service.create_category(CategoryCreate(title="Category B"))

    result = await category_service.get_all_categories_paginated(page=1, page_size=10)

    assert not isinstance(result, Error)
    assert len(result.data) == 2

    for category_data in result.data:
        assert hasattr(category_data, "subcategory_count")
        assert category_data.subcategory_count == 0  # Fake returns 0
