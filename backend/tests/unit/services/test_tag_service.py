import os
import sys

import pytest
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from configuration.tags.schemas import TagCreate, TagUpdate
from configuration.tags.service import TagServiceImpl
from schemas import Error, Message
from unit_of_work.fake_uow import FakeUnitOfWork


@pytest.fixture
def uow():
    """Provide a fake unit of work."""
    return FakeUnitOfWork()


@pytest.fixture
def tag_service(uow):
    """Provide a tag service with fake UoW."""
    return TagServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_create_tag_success(tag_service):
    """Test creating a new tag successfully."""
    tag_data = TagCreate(title="High Priority")

    result = await tag_service.create_tag(tag_data)

    assert not isinstance(result, Error)
    assert result.title == "high priority"


@pytest.mark.asyncio
async def test_create_tag_duplicate_title(tag_service):
    """Test creating a tag with duplicate title fails."""
    tag_data = TagCreate(title="Urgent")

    await tag_service.create_tag(tag_data)

    result = await tag_service.create_tag(tag_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_create_tag_duplicate_title_case_insensitive(tag_service):
    """Test creating a tag with duplicate title (case insensitive) fails."""
    tag_data1 = TagCreate(title="Important")
    tag_data2 = TagCreate(title="IMPORTANT")

    await tag_service.create_tag(tag_data1)

    result = await tag_service.create_tag(tag_data2)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_create_tag_trims_whitespace(tag_service):
    """Test creating a tag trims whitespace from title."""
    tag_data = TagCreate(title="  Trimmed Title  ")

    result = await tag_service.create_tag(tag_data)

    assert not isinstance(result, Error)
    assert result.title == "trimmed title"


@pytest.mark.asyncio
async def test_get_tag_by_id_success(tag_service):
    """Test retrieving a tag by ID."""
    tag_data = TagCreate(title="Test Tag")

    created = await tag_service.create_tag(tag_data)
    assert not isinstance(created, Error)

    result = await tag_service.get_tag_by_id(created.id)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.title == "test tag"


@pytest.mark.asyncio
async def test_get_tag_by_id_not_found(tag_service):
    """Test retrieving a non-existent tag returns error."""
    from uuid import uuid4

    result = await tag_service.get_tag_by_id(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_update_tag_success(tag_service):
    """Test updating a tag successfully."""
    tag_data = TagCreate(title="Original Tag")
    created = await tag_service.create_tag(tag_data)
    assert not isinstance(created, Error)

    update_data = TagUpdate(title="Updated Tag")
    result = await tag_service.update_tag(created.id, update_data)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.title == "updated tag"


@pytest.mark.asyncio
async def test_update_tag_not_found(tag_service):
    """Test updating a non-existent tag returns error."""
    from uuid import uuid4

    update_data = TagUpdate(title="Updated")
    result = await tag_service.update_tag(uuid4(), update_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_update_tag_duplicate_title(tag_service):
    """Test updating a tag with duplicate title fails."""
    tag1 = TagCreate(title="Tag One")
    tag2 = TagCreate(title="Tag Two")

    created1 = await tag_service.create_tag(tag1)
    created2 = await tag_service.create_tag(tag2)
    assert not isinstance(created1, Error)
    assert not isinstance(created2, Error)

    update_data = TagUpdate(title="Tag One")
    result = await tag_service.update_tag(created2.id, update_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_update_tag_same_title(tag_service):
    """Test updating a tag with the same title succeeds."""
    tag_data = TagCreate(title="Same Tag")
    created = await tag_service.create_tag(tag_data)
    assert not isinstance(created, Error)

    update_data = TagUpdate(title="Same Tag")
    result = await tag_service.update_tag(created.id, update_data)

    assert not isinstance(result, Error)
    assert result.title == "same tag"


@pytest.mark.asyncio
async def test_delete_tag_success(tag_service):
    """Test deleting a tag successfully."""
    tag_data = TagCreate(title="To Delete")
    created = await tag_service.create_tag(tag_data)
    assert not isinstance(created, Error)

    result = await tag_service.delete_tag(created.id)

    assert isinstance(result, Message)
    assert "deleted successfully" in result.detail.lower()

    get_result = await tag_service.get_tag_by_id(created.id)
    assert isinstance(get_result, Error)
    assert get_result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_tag_not_found(tag_service):
    """Test deleting a non-existent tag returns error."""
    from uuid import uuid4

    result = await tag_service.delete_tag(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_all_tags_paginated(tag_service):
    """Test retrieving paginated tags."""
    await tag_service.create_tag(TagCreate(title="Tag A"))
    await tag_service.create_tag(TagCreate(title="Tag B"))
    await tag_service.create_tag(TagCreate(title="Tag C"))

    result = await tag_service.get_all_tags_paginated(page=1, page_size=2)

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 3
    assert result.total_pages == 2
    assert result.has_next is True
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_get_all_tags_paginated_second_page(tag_service):
    """Test retrieving second page of paginated tags."""
    await tag_service.create_tag(TagCreate(title="Tag A"))
    await tag_service.create_tag(TagCreate(title="Tag B"))
    await tag_service.create_tag(TagCreate(title="Tag C"))

    result = await tag_service.get_all_tags_paginated(page=2, page_size=2)

    assert not isinstance(result, Error)
    assert len(result.data) == 1
    assert result.total_rows == 3
    assert result.total_pages == 2
    assert result.has_next is False
    assert result.has_previous is True


@pytest.mark.asyncio
async def test_get_all_tags_paginated_with_search(tag_service):
    """Test retrieving paginated tags with search."""
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
async def test_get_all_tags_paginated_empty_results(tag_service):
    """Test retrieving paginated tags with no results."""
    result = await tag_service.get_all_tags_paginated(page=1, page_size=10)

    assert not isinstance(result, Error)
    assert len(result.data) == 0
    assert result.total_rows == 0
    assert result.total_pages == 0
    assert result.has_next is False
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_get_all_tags_sorted_by_title(tag_service):
    """Test tags are sorted alphabetically by title."""
    await tag_service.create_tag(TagCreate(title="Zebra"))
    await tag_service.create_tag(TagCreate(title="Alpha"))
    await tag_service.create_tag(TagCreate(title="Beta"))

    result = await tag_service.get_all_tags_paginated(page=1, page_size=10)

    assert not isinstance(result, Error)
    assert len(result.data) == 3
    assert result.data[0].title == "alpha"
    assert result.data[1].title == "beta"
    assert result.data[2].title == "zebra"
