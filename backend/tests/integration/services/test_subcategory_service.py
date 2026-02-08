import os
import sys

import pytest
from sqlalchemy import select

sys.path.insert(0, f"{os.getcwd()}/src")

from configuration.categories.schemas import CategoryCreate  # noqa: E402
from configuration.categories.service import CategoryServiceImpl  # noqa: E402
from configuration.models import Subcategory  # noqa: E402
from configuration.subcategories.schemas import (  # noqa: E402
    SubcategoryCreate,
    SubcategoryUpdate,
)
from configuration.subcategories.service import SubcategoryServiceImpl  # noqa: E402
from db import default_session_factory  # noqa: E402
from schemas import Error  # noqa: E402
from unit_of_work.uow import UnitOfWorkImpl  # noqa: E402


@pytest.fixture
def category_service():
    """Provide category service with real database."""
    uow = UnitOfWorkImpl(session_factory=default_session_factory)
    return CategoryServiceImpl(unit_of_work=uow)


@pytest.fixture
def subcategory_service():
    """Provide subcategory service with real database."""
    uow = UnitOfWorkImpl(session_factory=default_session_factory)
    return SubcategoryServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_create_subcategory_commits_to_database(
    subcategory_service, category_service
):
    """Test that creating a subcategory commits data to database."""
    category = await category_service.create_category(CategoryCreate(title="Documents"))
    assert not isinstance(category, Error)

    subcategory_data = SubcategoryCreate(title="Reports", category_id=category.id)

    result = await subcategory_service.create_subcategory(subcategory_data)

    assert not isinstance(result, Error)
    assert result.id is not None

    async with default_session_factory() as session:
        stmt = select(Subcategory).where(Subcategory.id == result.id)
        db_result = await session.execute(stmt)
        db_subcategory = db_result.scalar_one_or_none()

        assert db_subcategory is not None
        assert db_subcategory.title == "reports"
        assert db_subcategory.category_id == category.id


@pytest.mark.asyncio
async def test_create_subcategory_with_invalid_category_fails(subcategory_service):
    """Test that creating a subcategory with invalid category fails."""
    from uuid import uuid4

    subcategory_data = SubcategoryCreate(title="Reports", category_id=uuid4())

    result = await subcategory_service.create_subcategory(subcategory_data)

    assert isinstance(result, Error)
    assert result.code == 404


@pytest.mark.asyncio
async def test_create_subcategory_duplicate_title_fails(
    subcategory_service, category_service
):
    """Test that creating a subcategory with duplicate title fails."""
    category = await category_service.create_category(CategoryCreate(title="Documents"))
    assert not isinstance(category, Error)

    subcategory_data = SubcategoryCreate(title="Approved", category_id=category.id)
    await subcategory_service.create_subcategory(subcategory_data)

    result = await subcategory_service.create_subcategory(subcategory_data)

    assert isinstance(result, Error)
    assert result.code == 400


@pytest.mark.asyncio
async def test_create_subcategory_case_insensitive_uniqueness(
    subcategory_service, category_service
):
    """Test that title uniqueness is case-insensitive."""
    category = await category_service.create_category(CategoryCreate(title="Documents"))
    assert not isinstance(category, Error)

    subcategory_data1 = SubcategoryCreate(title="Report", category_id=category.id)
    await subcategory_service.create_subcategory(subcategory_data1)

    subcategory_data2 = SubcategoryCreate(title="REPORT", category_id=category.id)
    result = await subcategory_service.create_subcategory(subcategory_data2)

    assert isinstance(result, Error)
    assert result.code == 400


@pytest.mark.asyncio
async def test_get_subcategory_by_id_returns_from_database(
    subcategory_service, category_service
):
    """Test that getting a subcategory by ID retrieves from database."""
    category = await category_service.create_category(CategoryCreate(title="Documents"))
    assert not isinstance(category, Error)

    subcategory_data = SubcategoryCreate(title="Reports", category_id=category.id)
    created = await subcategory_service.create_subcategory(subcategory_data)
    assert not isinstance(created, Error)

    result = await subcategory_service.get_subcategory_by_id(created.id)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.title == "reports"


@pytest.mark.asyncio
async def test_update_subcategory_commits_to_database(
    subcategory_service, category_service
):
    """Test that updating a subcategory commits changes to database."""
    category = await category_service.create_category(CategoryCreate(title="Documents"))
    assert not isinstance(category, Error)

    subcategory_data = SubcategoryCreate(title="Report", category_id=category.id)
    created = await subcategory_service.create_subcategory(subcategory_data)
    assert not isinstance(created, Error)

    update_data = SubcategoryUpdate(title="Final Report", category_id=category.id)
    result = await subcategory_service.update_subcategory(created.id, update_data)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(Subcategory).where(Subcategory.id == created.id)
        db_result = await session.execute(stmt)
        db_subcategory = db_result.scalar_one_or_none()

        assert db_subcategory is not None
        assert db_subcategory.title == "final report"


@pytest.mark.asyncio
async def test_update_subcategory_change_category(
    subcategory_service, category_service
):
    """Test that updating a subcategory can change its category."""
    category1 = await category_service.create_category(
        CategoryCreate(title="Documents")
    )
    category2 = await category_service.create_category(CategoryCreate(title="Projects"))
    assert not isinstance(category1, Error)
    assert not isinstance(category2, Error)

    subcategory_data = SubcategoryCreate(title="Report", category_id=category1.id)
    created = await subcategory_service.create_subcategory(subcategory_data)
    assert not isinstance(created, Error)

    update_data = SubcategoryUpdate(title="Report", category_id=category2.id)
    result = await subcategory_service.update_subcategory(created.id, update_data)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(Subcategory).where(Subcategory.id == created.id)
        db_result = await session.execute(stmt)
        db_subcategory = db_result.scalar_one_or_none()

        assert db_subcategory is not None
        assert db_subcategory.category_id == category2.id


@pytest.mark.asyncio
async def test_update_subcategory_duplicate_title_fails(
    subcategory_service, category_service
):
    """Test that updating a subcategory with duplicate title fails."""
    category = await category_service.create_category(CategoryCreate(title="Documents"))
    assert not isinstance(category, Error)

    subcategory1 = SubcategoryCreate(title="Subcategory One", category_id=category.id)
    subcategory2 = SubcategoryCreate(title="Subcategory Two", category_id=category.id)

    created1 = await subcategory_service.create_subcategory(subcategory1)
    created2 = await subcategory_service.create_subcategory(subcategory2)
    assert not isinstance(created1, Error)
    assert not isinstance(created2, Error)

    update_data = SubcategoryUpdate(title="Subcategory One", category_id=category.id)
    result = await subcategory_service.update_subcategory(created2.id, update_data)

    assert isinstance(result, Error)
    assert result.code == 400


@pytest.mark.asyncio
async def test_update_subcategory_same_title_succeeds(
    subcategory_service, category_service
):
    """Test that updating a subcategory with the same title succeeds."""
    category = await category_service.create_category(CategoryCreate(title="Documents"))
    assert not isinstance(category, Error)

    subcategory_data = SubcategoryCreate(title="Report", category_id=category.id)
    created = await subcategory_service.create_subcategory(subcategory_data)
    assert not isinstance(created, Error)

    update_data = SubcategoryUpdate(title="Report", category_id=category.id)
    result = await subcategory_service.update_subcategory(created.id, update_data)

    assert not isinstance(result, Error)


@pytest.mark.asyncio
async def test_update_subcategory_invalid_category_fails(
    subcategory_service, category_service
):
    """Test that updating a subcategory with invalid category fails."""
    from uuid import uuid4

    category = await category_service.create_category(CategoryCreate(title="Documents"))
    assert not isinstance(category, Error)

    subcategory_data = SubcategoryCreate(title="Report", category_id=category.id)
    created = await subcategory_service.create_subcategory(subcategory_data)
    assert not isinstance(created, Error)

    update_data = SubcategoryUpdate(title="Report", category_id=uuid4())
    result = await subcategory_service.update_subcategory(created.id, update_data)

    assert isinstance(result, Error)
    assert result.code == 404


@pytest.mark.asyncio
async def test_delete_subcategory_hard_deletes_in_database(
    subcategory_service, category_service
):
    """Test that deleting a subcategory removes it from database (hard delete)."""
    category = await category_service.create_category(CategoryCreate(title="Documents"))
    assert not isinstance(category, Error)

    subcategory_data = SubcategoryCreate(title="To Delete", category_id=category.id)
    created = await subcategory_service.create_subcategory(subcategory_data)
    assert not isinstance(created, Error)

    result = await subcategory_service.delete_subcategory(created.id)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(Subcategory).where(Subcategory.id == created.id)
        db_result = await session.execute(stmt)
        db_subcategory = db_result.scalar_one_or_none()

        assert db_subcategory is None


@pytest.mark.asyncio
async def test_get_all_subcategories_paginated_from_database(
    subcategory_service, category_service
):
    """Test that getting paginated subcategories retrieves from database."""
    category = await category_service.create_category(CategoryCreate(title="Documents"))
    assert not isinstance(category, Error)

    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory A", category_id=category.id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory B", category_id=category.id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory C", category_id=category.id)
    )

    result = await subcategory_service.get_all_subcategories_paginated(
        page=1, page_size=2
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 3
    assert result.total_pages == 2


@pytest.mark.asyncio
async def test_get_all_subcategories_search_in_database(
    subcategory_service, category_service
):
    """Test that searching subcategories works with database."""
    category = await category_service.create_category(CategoryCreate(title="Documents"))
    assert not isinstance(category, Error)

    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Report", category_id=category.id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Final Report", category_id=category.id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Project", category_id=category.id)
    )

    result = await subcategory_service.get_all_subcategories_paginated(
        page=1, page_size=10, search="report"
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 2


@pytest.mark.asyncio
async def test_get_all_subcategories_filter_by_category(
    subcategory_service, category_service
):
    """Test that filtering subcategories by category works."""
    category1 = await category_service.create_category(
        CategoryCreate(title="Documents")
    )
    category2 = await category_service.create_category(CategoryCreate(title="Projects"))
    assert not isinstance(category1, Error)
    assert not isinstance(category2, Error)

    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory A", category_id=category1.id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory B", category_id=category1.id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory C", category_id=category2.id)
    )

    result = await subcategory_service.get_all_subcategories_paginated(
        page=1, page_size=10, category_id=category1.id
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 2
    assert all(sub.category_id == category1.id for sub in result.data)


@pytest.mark.asyncio
async def test_get_all_subcategories_by_category(subcategory_service, category_service):
    """Test that getting all subcategories by category works."""
    category = await category_service.create_category(CategoryCreate(title="Documents"))
    assert not isinstance(category, Error)

    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory A", category_id=category.id)
    )
    await subcategory_service.create_subcategory(
        SubcategoryCreate(title="Subcategory B", category_id=category.id)
    )

    result = await subcategory_service.get_all_subcategories_by_category(category.id)

    assert not isinstance(result, Error)
    assert len(result) == 2
    assert all(sub.category_id == category.id for sub in result)
    assert all(sub.category_title == "documents" for sub in result)


@pytest.mark.asyncio
async def test_get_all_subcategories_by_invalid_category_fails(subcategory_service):
    """Test that getting subcategories by invalid category fails."""
    from uuid import uuid4

    result = await subcategory_service.get_all_subcategories_by_category(uuid4())

    assert isinstance(result, Error)
    assert result.code == 404


@pytest.mark.asyncio
async def test_get_all_subcategories_paginated_with_invalid_category_fails(
    subcategory_service,
):
    """Test that filtering by invalid category fails."""
    from uuid import uuid4

    result = await subcategory_service.get_all_subcategories_paginated(
        page=1, page_size=10, category_id=uuid4()
    )

    assert isinstance(result, Error)
    assert result.code == 404
