import os
import sys

import pytest
from sqlalchemy import select

sys.path.insert(0, f"{os.getcwd()}/src")

from configuration.models import Tag  # noqa: E402
from configuration.tags.schemas import TagCreate, TagUpdate  # noqa: E402
from configuration.tags.service import TagServiceImpl  # noqa: E402
from db import default_session_factory  # noqa: E402
from schemas import Error  # noqa: E402
from unit_of_work.uow import UnitOfWorkImpl  # noqa: E402


@pytest.fixture
def tag_service():
    """Provide tag service with real database."""
    uow = UnitOfWorkImpl(session_factory=default_session_factory)
    return TagServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_create_tag_commits_to_database(tag_service):
    """Test that creating a tag commits data to database."""
    tag_data = TagCreate(title="High Priority")

    result = await tag_service.create_tag(tag_data)

    assert not isinstance(result, Error)
    assert result.id is not None

    async with default_session_factory() as session:
        stmt = select(Tag).where(Tag.id == result.id)
        db_result = await session.execute(stmt)
        db_tag = db_result.scalar_one_or_none()

        assert db_tag is not None
        assert db_tag.title == "high priority"


@pytest.mark.asyncio
async def test_create_tag_duplicate_title_fails(tag_service):
    """Test that creating a tag with duplicate title fails."""
    tag_data = TagCreate(title="Urgent")
    await tag_service.create_tag(tag_data)

    result = await tag_service.create_tag(tag_data)

    assert isinstance(result, Error)
    assert result.code == 400


@pytest.mark.asyncio
async def test_create_tag_case_insensitive_uniqueness(tag_service):
    """Test that title uniqueness is case-insensitive."""
    tag_data1 = TagCreate(title="Important")
    await tag_service.create_tag(tag_data1)

    tag_data2 = TagCreate(title="IMPORTANT")
    result = await tag_service.create_tag(tag_data2)

    assert isinstance(result, Error)
    assert result.code == 400


@pytest.mark.asyncio
async def test_create_tag_trims_whitespace(tag_service):
    """Test that creating a tag trims whitespace."""
    tag_data = TagCreate(title="  Trimmed  ")

    result = await tag_service.create_tag(tag_data)

    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(Tag).where(Tag.id == result.id)
        db_result = await session.execute(stmt)
        db_tag = db_result.scalar_one_or_none()

        assert db_tag is not None
        assert db_tag.title == "trimmed"


@pytest.mark.asyncio
async def test_get_tag_by_id_returns_from_database(tag_service):
    """Test that getting a tag by ID retrieves from database."""
    tag_data = TagCreate(title="Test Tag")
    created = await tag_service.create_tag(tag_data)
    assert not isinstance(created, Error)

    result = await tag_service.get_tag_by_id(created.id)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.title == "test tag"


@pytest.mark.asyncio
async def test_update_tag_commits_to_database(tag_service):
    """Test that updating a tag commits changes to database."""
    tag_data = TagCreate(title="Original")
    created = await tag_service.create_tag(tag_data)
    assert not isinstance(created, Error)

    update_data = TagUpdate(title="Updated")
    result = await tag_service.update_tag(created.id, update_data)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(Tag).where(Tag.id == created.id)
        db_result = await session.execute(stmt)
        db_tag = db_result.scalar_one_or_none()

        assert db_tag is not None
        assert db_tag.title == "updated"


@pytest.mark.asyncio
async def test_update_tag_duplicate_title_fails(tag_service):
    """Test that updating a tag with duplicate title fails."""
    tag1 = TagCreate(title="Tag One")
    tag2 = TagCreate(title="Tag Two")

    created1 = await tag_service.create_tag(tag1)
    created2 = await tag_service.create_tag(tag2)
    assert not isinstance(created1, Error)
    assert not isinstance(created2, Error)

    update_data = TagUpdate(title="Tag One")
    result = await tag_service.update_tag(created2.id, update_data)

    assert isinstance(result, Error)
    assert result.code == 400


@pytest.mark.asyncio
async def test_update_tag_same_title_succeeds(tag_service):
    """Test that updating a tag with the same title succeeds."""
    tag_data = TagCreate(title="Same Tag")
    created = await tag_service.create_tag(tag_data)
    assert not isinstance(created, Error)

    update_data = TagUpdate(title="Same Tag")
    result = await tag_service.update_tag(created.id, update_data)

    assert not isinstance(result, Error)
    assert result.title == "same tag"


@pytest.mark.asyncio
async def test_delete_tag_hard_deletes_in_database(tag_service):
    """Test that deleting a tag removes it from database (hard delete)."""
    tag_data = TagCreate(title="To Delete")
    created = await tag_service.create_tag(tag_data)
    assert not isinstance(created, Error)

    result = await tag_service.delete_tag(created.id)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(Tag).where(Tag.id == created.id)
        db_result = await session.execute(stmt)
        db_tag = db_result.scalar_one_or_none()

        assert db_tag is None


@pytest.mark.asyncio
async def test_get_all_tags_paginated_from_database(tag_service):
    """Test that getting paginated tags retrieves from database."""
    await tag_service.create_tag(TagCreate(title="Tag A"))
    await tag_service.create_tag(TagCreate(title="Tag B"))
    await tag_service.create_tag(TagCreate(title="Tag C"))

    result = await tag_service.get_all_tags_paginated(page=1, page_size=2)

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 3
    assert result.total_pages == 2


@pytest.mark.asyncio
async def test_get_all_tags_search_in_database(tag_service):
    """Test that searching tags works with database."""
    await tag_service.create_tag(TagCreate(title="Important Task"))
    await tag_service.create_tag(TagCreate(title="Urgent"))
    await tag_service.create_tag(TagCreate(title="Task Complete"))

    result = await tag_service.get_all_tags_paginated(
        page=1, page_size=10, search="task"
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 2


@pytest.mark.asyncio
async def test_get_all_tags_sorted_alphabetically(tag_service):
    """Test that tags are sorted alphabetically by title."""
    await tag_service.create_tag(TagCreate(title="Zebra"))
    await tag_service.create_tag(TagCreate(title="Alpha"))
    await tag_service.create_tag(TagCreate(title="Beta"))

    result = await tag_service.get_all_tags_paginated(page=1, page_size=10)

    assert not isinstance(result, Error)
    assert len(result.data) == 3
    assert result.data[0].title == "alpha"
    assert result.data[1].title == "beta"
    assert result.data[2].title == "zebra"
