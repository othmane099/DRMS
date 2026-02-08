import os
import sys

import pytest
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from configuration.categories.schemas import CategoryCreate
from configuration.subcategories.schemas import SubcategoryCreate, SubcategoryUpdate
from configuration.subcategories.service import SubcategoryServiceImpl
from schemas import Error, Message
from unit_of_work.fake_uow import FakeUnitOfWork


@pytest.fixture
def uow():
    """Provide a fake unit of work."""
    return FakeUnitOfWork()


@pytest.fixture
async def category_id(uow):
    """Create a test category and return its ID."""
    category = await uow.category_repository.create_category(
        CategoryCreate(title="Test Category")
    )
    return category.id


@pytest.fixture
def subcategory_service(uow):
    """Provide a subcategory service with fake UoW."""
    return SubcategoryServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_create_subcategory_success(subcategory_service, category_id):
    """Test creating a new subcategory successfully."""
    subcategory_data = SubcategoryCreate(title="Reports", category_id=category_id)

    result = await subcategory_service.create_subcategory(subcategory_data)

    assert not isinstance(result, Error)
    assert result.title == "reports"
    assert result.category_id == category_id


@pytest.mark.asyncio
async def test_create_subcategory_invalid_category(subcategory_service):
    """Test creating a subcategory with invalid category fails."""
    from uuid import uuid4

    subcategory_data = SubcategoryCreate(title="Reports", category_id=uuid4())

    result = await subcategory_service.create_subcategory(subcategory_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "category not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_create_subcategory_duplicate_title(subcategory_service, category_id):
    """Test creating a subcategory with duplicate title fails."""
    subcategory_data = SubcategoryCreate(title="Reports", category_id=category_id)

    await subcategory_service.create_subcategory(subcategory_data)

    result = await subcategory_service.create_subcategory(subcategory_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_create_subcategory_duplicate_title_case_insensitive(
    subcategory_service, category_id
):
    """Test creating a subcategory with duplicate title (case insensitive) fails."""
    subcategory_data1 = SubcategoryCreate(title="Reports", category_id=category_id)
    subcategory_data2 = SubcategoryCreate(title="REPORTS", category_id=category_id)

    await subcategory_service.create_subcategory(subcategory_data1)

    result = await subcategory_service.create_subcategory(subcategory_data2)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_subcategory_by_id_success(subcategory_service, category_id):
    """Test retrieving a subcategory by ID."""
    subcategory_data = SubcategoryCreate(title="Reports", category_id=category_id)

    created = await subcategory_service.create_subcategory(subcategory_data)
    assert not isinstance(created, Error)

    result = await subcategory_service.get_subcategory_by_id(created.id)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.title == "reports"


@pytest.mark.asyncio
async def test_get_subcategory_by_id_not_found(subcategory_service):
    """Test retrieving a non-existent subcategory returns error."""
    from uuid import uuid4

    result = await subcategory_service.get_subcategory_by_id(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_update_subcategory_success(subcategory_service, category_id):
    """Test updating a subcategory successfully."""
    subcategory_data = SubcategoryCreate(title="Reports", category_id=category_id)
    created = await subcategory_service.create_subcategory(subcategory_data)
    assert not isinstance(created, Error)

    update_data = SubcategoryUpdate(title="Final Reports", category_id=category_id)
    result = await subcategory_service.update_subcategory(created.id, update_data)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.title == "final reports"


@pytest.mark.asyncio
async def test_update_subcategory_change_category(
    subcategory_service, uow, category_id
):
    """Test updating a subcategory to a different category."""
    category2 = await uow.category_repository.create_category(
        CategoryCreate(title="Category 2")
    )

    subcategory_data = SubcategoryCreate(title="Reports", category_id=category_id)
    created = await subcategory_service.create_subcategory(subcategory_data)
    assert not isinstance(created, Error)

    update_data = SubcategoryUpdate(title="Reports", category_id=category2.id)
    result = await subcategory_service.update_subcategory(created.id, update_data)

    assert not isinstance(result, Error)
    assert result.category_id == category2.id


@pytest.mark.asyncio
async def test_update_subcategory_invalid_new_category(
    subcategory_service, category_id
):
    """Test updating a subcategory to an invalid category fails."""
    from uuid import uuid4

    subcategory_data = SubcategoryCreate(title="Reports", category_id=category_id)
    created = await subcategory_service.create_subcategory(subcategory_data)
    assert not isinstance(created, Error)

    update_data = SubcategoryUpdate(title="Reports", category_id=uuid4())
    result = await subcategory_service.update_subcategory(created.id, update_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "category not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_update_subcategory_not_found(subcategory_service, category_id):
    """Test updating a non-existent subcategory returns error."""
    from uuid import uuid4

    update_data = SubcategoryUpdate(title="Reports", category_id=category_id)
    result = await subcategory_service.update_subcategory(uuid4(), update_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_update_subcategory_duplicate_title(subcategory_service, category_id):
    """Test updating a subcategory with duplicate title fails."""
    subcategory1 = SubcategoryCreate(title="Subcategory One", category_id=category_id)
    subcategory2 = SubcategoryCreate(title="Subcategory Two", category_id=category_id)

    created1 = await subcategory_service.create_subcategory(subcategory1)
    created2 = await subcategory_service.create_subcategory(subcategory2)
    assert not isinstance(created1, Error)
    assert not isinstance(created2, Error)

    update_data = SubcategoryUpdate(title="Subcategory One", category_id=category_id)
    result = await subcategory_service.update_subcategory(created2.id, update_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_update_subcategory_same_title(subcategory_service, category_id):
    """Test updating a subcategory with the same title succeeds."""
    subcategory_data = SubcategoryCreate(title="Reports", category_id=category_id)
    created = await subcategory_service.create_subcategory(subcategory_data)
    assert not isinstance(created, Error)

    update_data = SubcategoryUpdate(title="Reports", category_id=category_id)
    result = await subcategory_service.update_subcategory(created.id, update_data)

    assert not isinstance(result, Error)


@pytest.mark.asyncio
async def test_delete_subcategory_success(subcategory_service, category_id):
    """Test deleting a subcategory successfully."""
    subcategory_data = SubcategoryCreate(title="To Delete", category_id=category_id)
    created = await subcategory_service.create_subcategory(subcategory_data)
    assert not isinstance(created, Error)

    result = await subcategory_service.delete_subcategory(created.id)

    assert isinstance(result, Message)
    assert "deleted successfully" in result.detail.lower()

    get_result = await subcategory_service.get_subcategory_by_id(created.id)
    assert isinstance(get_result, Error)
    assert get_result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_subcategory_not_found(subcategory_service):
    """Test deleting a non-existent subcategory returns error."""
    from uuid import uuid4

    result = await subcategory_service.delete_subcategory(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_all_subcategories_paginated(subcategory_service, category_id):
    """Test retrieving paginated subcategories."""
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory A", category_id=category_id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory B", category_id=category_id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory C", category_id=category_id)
    )

    result = await subcategory_service.get_all_subcategories_paginated(
        page=1, page_size=2
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 3
    assert result.total_pages == 2
    assert result.has_next is True
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_get_all_subcategories_paginated_with_search(
    subcategory_service, category_id
):
    """Test retrieving paginated subcategories with search."""
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Reports", category_id=category_id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="HSE", category_id=category_id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Final Reports", category_id=category_id)
    )

    result = await subcategory_service.get_all_subcategories_paginated(
        page=1, page_size=10, search="report"
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 2


@pytest.mark.asyncio
async def test_get_all_subcategories_paginated_with_category_filter(
    subcategory_service, uow, category_id
):
    """Test retrieving paginated subcategories filtered by category."""
    category2 = await uow.category_repository.create_category(
        CategoryCreate(title="Category 2")
    )

    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory 1", category_id=category_id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory 2", category_id=category_id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory 3", category_id=category2.id)
    )

    result = await subcategory_service.get_all_subcategories_paginated(
        page=1, page_size=10, category_id=category_id
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 2


@pytest.mark.asyncio
async def test_get_all_subcategories_paginated_invalid_category(subcategory_service):
    """Test retrieving subcategories with invalid category returns error."""
    from uuid import uuid4

    result = await subcategory_service.get_all_subcategories_paginated(
        page=1, page_size=10, category_id=uuid4()
    )

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "category not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_all_subcategories_by_category(subcategory_service, category_id):
    """Test retrieving all subcategories for a category without pagination."""
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory 1", category_id=category_id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory 2", category_id=category_id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory 3", category_id=category_id)
    )

    result = await subcategory_service.get_all_subcategories_by_category(category_id)

    assert not isinstance(result, Error)
    assert len(result) == 3
    assert all(sub.category_id == category_id for sub in result)


@pytest.mark.asyncio
async def test_get_all_subcategories_by_category_invalid_category(subcategory_service):
    """Test retrieving subcategories for invalid category returns error."""
    from uuid import uuid4

    result = await subcategory_service.get_all_subcategories_by_category(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "category not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_all_subcategories_by_category_empty(
    subcategory_service, category_id
):
    """Test retrieving subcategories for category with no subcategories."""
    result = await subcategory_service.get_all_subcategories_by_category(category_id)

    assert not isinstance(result, Error)
    assert len(result) == 0
