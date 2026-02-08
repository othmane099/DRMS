import os
import sys

import pytest
from fastapi import HTTPException
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from configuration.tags.api import (
    create_tag,
    delete_tag,
    get_tag,
    get_tags,
    update_tag,
)
from configuration.tags.fakes import FakeTagService
from configuration.tags.schemas import TagCreate, TagUpdate


@pytest.fixture
def tag_service():
    """Provide a fake tag service."""
    return FakeTagService()


@pytest.mark.asyncio
async def test_get_tags_api(tag_service):
    """Test GET /tags endpoint."""
    await tag_service.create_tag(TagCreate(title="Tag 1"))
    await tag_service.create_tag(TagCreate(title="Tag 2"))

    result = await get_tags(page=1, page_size=10, search=None, tag_service=tag_service)

    assert result.total_rows == 2
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_get_tags_api_with_pagination(tag_service):
    """Test GET /tags endpoint with pagination."""
    for i in range(5):
        await tag_service.create_tag(TagCreate(title=f"Tag {i}"))

    result = await get_tags(page=1, page_size=2, search=None, tag_service=tag_service)

    assert result.total_rows == 5
    assert len(result.data) == 2
    assert result.total_pages == 3
    assert result.has_next is True


@pytest.mark.asyncio
async def test_get_tags_api_with_search(tag_service):
    """Test GET /tags endpoint with search."""
    await tag_service.create_tag(TagCreate(title="Important Task"))
    await tag_service.create_tag(TagCreate(title="Urgent"))
    await tag_service.create_tag(TagCreate(title="Task Complete"))

    result = await get_tags(
        page=1, page_size=10, search="task", tag_service=tag_service
    )

    assert result.total_rows == 2
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_get_tag_api_success(tag_service):
    """Test GET /tags/{id} endpoint with valid ID."""
    created = await tag_service.create_tag(TagCreate(title="Test Tag"))

    result = await get_tag(tag_id=created.id, tag_service=tag_service)

    assert result.id == created.id
    assert result.title == "test tag"


@pytest.mark.asyncio
async def test_get_tag_api_not_found(tag_service):
    """Test GET /tags/{id} endpoint with invalid ID."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await get_tag(tag_id=uuid4(), tag_service=tag_service)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_tag_api_success(tag_service):
    """Test POST /tags endpoint."""
    tag_data = TagCreate(title="New Tag")

    result = await create_tag(tag_create=tag_data, tag_service=tag_service)

    assert result.title == "new tag"


@pytest.mark.asyncio
async def test_create_tag_api_duplicate_title(tag_service):
    """Test POST /tags endpoint with duplicate title."""
    tag_data = TagCreate(title="Duplicate")

    await tag_service.create_tag(tag_data)

    with pytest.raises(HTTPException) as exc_info:
        await create_tag(tag_create=tag_data, tag_service=tag_service)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_create_tag_api_converts_title_to_lowercase(tag_service):
    """Test POST /tags endpoint converts title to lowercase."""
    tag_data = TagCreate(title="UPPERCASE TITLE")

    result = await create_tag(tag_create=tag_data, tag_service=tag_service)

    assert result.title == "uppercase title"


@pytest.mark.asyncio
async def test_create_tag_api_trims_whitespace(tag_service):
    """Test POST /tags endpoint trims whitespace."""
    tag_data = TagCreate(title="  Trimmed  ")

    result = await create_tag(tag_create=tag_data, tag_service=tag_service)

    assert result.title == "trimmed"


@pytest.mark.asyncio
async def test_update_tag_api_success(tag_service):
    """Test PUT /tags/{id} endpoint."""
    created = await tag_service.create_tag(TagCreate(title="Original"))

    update_data = TagUpdate(title="Updated")
    result = await update_tag(
        tag_id=created.id, tag_update=update_data, tag_service=tag_service
    )

    assert result.id == created.id
    assert result.title == "updated"


@pytest.mark.asyncio
async def test_update_tag_api_not_found(tag_service):
    """Test PUT /tags/{id} endpoint with invalid ID."""
    from uuid import uuid4

    update_data = TagUpdate(title="Updated")

    with pytest.raises(HTTPException) as exc_info:
        await update_tag(
            tag_id=uuid4(), tag_update=update_data, tag_service=tag_service
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_tag_api_duplicate_title(tag_service):
    """Test PUT /tags/{id} endpoint with duplicate title."""
    await tag_service.create_tag(TagCreate(title="Tag 1"))
    tag2 = await tag_service.create_tag(TagCreate(title="Tag 2"))

    update_data = TagUpdate(title="Tag 1")

    with pytest.raises(HTTPException) as exc_info:
        await update_tag(
            tag_id=tag2.id, tag_update=update_data, tag_service=tag_service
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_delete_tag_api_success(tag_service):
    """Test DELETE /tags/{id} endpoint."""
    created = await tag_service.create_tag(TagCreate(title="To Delete"))

    result = await delete_tag(tag_id=created.id, tag_service=tag_service)

    assert "deleted successfully" in result.detail.lower()


@pytest.mark.asyncio
async def test_delete_tag_api_not_found(tag_service):
    """Test DELETE /tags/{id} endpoint with invalid ID."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await delete_tag(tag_id=uuid4(), tag_service=tag_service)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_tag_validates_max_length():
    """Test POST /tags endpoint validates title max length."""
    long_title = "a" * 256

    with pytest.raises(ValueError):
        TagCreate(title=long_title)


@pytest.mark.asyncio
async def test_get_tags_empty_results(tag_service):
    """Test GET /tags endpoint with no tags."""
    result = await get_tags(page=1, page_size=10, search=None, tag_service=tag_service)

    assert result.total_rows == 0
    assert len(result.data) == 0
    assert result.total_pages == 0


@pytest.mark.asyncio
async def test_get_tags_sorted_alphabetically(tag_service):
    """Test GET /tags endpoint returns tags sorted alphabetically."""
    await tag_service.create_tag(TagCreate(title="Zebra"))
    await tag_service.create_tag(TagCreate(title="Alpha"))
    await tag_service.create_tag(TagCreate(title="Beta"))

    result = await get_tags(page=1, page_size=10, search=None, tag_service=tag_service)

    assert len(result.data) == 3
    assert result.data[0].title == "alpha"
    assert result.data[1].title == "beta"
    assert result.data[2].title == "zebra"
