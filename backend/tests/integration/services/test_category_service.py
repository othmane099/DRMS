import os
import sys

import pytest
from sqlalchemy import select

sys.path.insert(0, f"{os.getcwd()}/src")

from configuration.categories.schemas import (  # noqa: E402
    CategoryCreate,
    CategoryUpdate,
)
from configuration.categories.service import CategoryServiceImpl  # noqa: E402
from configuration.models import Category  # noqa: E402
from db import default_session_factory  # noqa: E402
from schemas import Error  # noqa: E402
from unit_of_work.uow import UnitOfWorkImpl  # noqa: E402


@pytest.fixture
def category_service():
    """Provide category service with real database."""
    uow = UnitOfWorkImpl(session_factory=default_session_factory)
    return CategoryServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_create_category_commits_to_database(category_service):
    """Test that creating a category commits data to database."""
    category_data = CategoryCreate(title="Reports")

    result = await category_service.create_category(category_data)

    assert not isinstance(result, Error)
    assert result.id is not None

    async with default_session_factory() as session:
        stmt = select(Category).where(Category.id == result.id)
        db_result = await session.execute(stmt)
        db_category = db_result.scalar_one_or_none()

        assert db_category is not None
        assert db_category.title == "reports"


@pytest.mark.asyncio
async def test_create_category_duplicate_title_fails(category_service):
    """Test that creating a category with duplicate title fails."""
    category_data = CategoryCreate(title="Approved")
    await category_service.create_category(category_data)

    result = await category_service.create_category(category_data)

    assert isinstance(result, Error)
    assert result.code == 400


@pytest.mark.asyncio
async def test_create_category_case_insensitive_uniqueness(category_service):
    """Test that title uniqueness is case-insensitive."""
    category_data1 = CategoryCreate(title="Report")
    await category_service.create_category(category_data1)

    category_data2 = CategoryCreate(title="REPORT")
    result = await category_service.create_category(category_data2)

    assert isinstance(result, Error)
    assert result.code == 400


@pytest.mark.asyncio
async def test_get_category_by_id_returns_from_database(category_service):
    """Test that getting a category by ID retrieves from database."""
    category_data = CategoryCreate(title="Reports")
    created = await category_service.create_category(category_data)
    assert not isinstance(created, Error)

    result = await category_service.get_category_by_id(created.id)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.title == "reports"


@pytest.mark.asyncio
async def test_update_category_commits_to_database(category_service):
    """Test that updating a category commits changes to database."""
    category_data = CategoryCreate(title="Report")
    created = await category_service.create_category(category_data)
    assert not isinstance(created, Error)

    update_data = CategoryUpdate(title="Final Report")
    result = await category_service.update_category(created.id, update_data)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(Category).where(Category.id == created.id)
        db_result = await session.execute(stmt)
        db_category = db_result.scalar_one_or_none()

        assert db_category is not None
        assert db_category.title == "final report"


@pytest.mark.asyncio
async def test_update_category_duplicate_title_fails(category_service):
    """Test that updating a category with duplicate title fails."""
    category1 = CategoryCreate(title="Category One")
    category2 = CategoryCreate(title="Category Two")

    created1 = await category_service.create_category(category1)
    created2 = await category_service.create_category(category2)
    assert not isinstance(created1, Error)
    assert not isinstance(created2, Error)

    update_data = CategoryUpdate(title="Category One")
    result = await category_service.update_category(created2.id, update_data)

    assert isinstance(result, Error)
    assert result.code == 400


@pytest.mark.asyncio
async def test_update_category_same_title_succeeds(category_service):
    """Test that updating a category with the same title succeeds."""
    category_data = CategoryCreate(title="Report")
    created = await category_service.create_category(category_data)
    assert not isinstance(created, Error)

    update_data = CategoryUpdate(title="Report")
    result = await category_service.update_category(created.id, update_data)

    assert not isinstance(result, Error)


@pytest.mark.asyncio
async def test_delete_category_hard_deletes_in_database(category_service):
    """Test that deleting a category removes it from database (hard delete)."""
    category_data = CategoryCreate(title="To Delete")
    created = await category_service.create_category(category_data)
    assert not isinstance(created, Error)

    result = await category_service.delete_category(created.id)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(Category).where(Category.id == created.id)
        db_result = await session.execute(stmt)
        db_category = db_result.scalar_one_or_none()

        assert db_category is None


@pytest.mark.asyncio
async def test_get_all_categories_paginated_from_database(category_service):
    """Test that getting paginated categories retrieves from database."""
    await category_service.create_category(CategoryCreate(title="Category A"))
    await category_service.create_category(CategoryCreate(title="Category B"))
    await category_service.create_category(CategoryCreate(title="Category C"))

    result = await category_service.get_all_categories_paginated(page=1, page_size=2)

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 3
    assert result.total_pages == 2


@pytest.mark.asyncio
async def test_get_all_categories_search_in_database(category_service):
    """Test that searching categories works with database."""
    await category_service.create_category(CategoryCreate(title="Report"))
    await category_service.create_category(CategoryCreate(title="Final Report"))
    await category_service.create_category(CategoryCreate(title="Project"))

    result = await category_service.get_all_categories_paginated(
        page=1, page_size=10, search="report"
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 2


@pytest.mark.asyncio
async def test_get_all_categories_includes_subcategory_count(category_service):
    """Test that paginated categories include subcategory_count from database."""
    from configuration.models import Subcategory

    category1 = await category_service.create_category(
        CategoryCreate(title="Category 1")
    )
    category2 = await category_service.create_category(
        CategoryCreate(title="Category 2")
    )
    assert not isinstance(category1, Error)
    assert not isinstance(category2, Error)

    async with default_session_factory() as session:
        subcategory1 = Subcategory(title="Subcategory 1", category_id=category1.id)
        subcategory2 = Subcategory(title="Subcategory 2", category_id=category1.id)
        subcategory3 = Subcategory(title="Subcategory 3", category_id=category2.id)
        session.add(subcategory1)
        session.add(subcategory2)
        session.add(subcategory3)
        await session.commit()

    result = await category_service.get_all_categories_paginated(page=1, page_size=10)

    assert not isinstance(result, Error)
    assert len(result.data) == 2

    for category_data in result.data:
        assert hasattr(category_data, "subcategory_count")
        if category_data.id == category1.id:
            assert category_data.subcategory_count == 2
        elif category_data.id == category2.id:
            assert category_data.subcategory_count == 1


@pytest.mark.asyncio
async def test_get_all_categories_subcategory_count_zero_when_no_subcategories(
    category_service,
):
    """Test that subcategory_count is 0 when category has no subcategories."""
    category = await category_service.create_category(CategoryCreate(title="Category"))
    assert not isinstance(category, Error)

    result = await category_service.get_all_categories_paginated(page=1, page_size=10)

    assert not isinstance(result, Error)
    assert len(result.data) == 1
    assert result.data[0].subcategory_count == 0
