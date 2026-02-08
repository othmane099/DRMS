import os
import sys

import pytest
from fastapi import HTTPException
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from configuration.stages.api import (
    create_stage,
    delete_stage,
    get_stage,
    get_stages,
    update_stage,
)
from configuration.stages.fakes import FakeStageService
from configuration.stages.schemas import StageCreate, StageUpdate


@pytest.fixture
def stage_service():
    """Provide a fake stage service."""
    return FakeStageService()


@pytest.mark.asyncio
async def test_get_stages_api(stage_service):
    """Test GET /stages endpoint."""
    await stage_service.create_stage(StageCreate(title="Stage 1", color="#FF0000"))
    await stage_service.create_stage(StageCreate(title="Stage 2", color="#00FF00"))

    result = await get_stages(
        page=1, page_size=10, search=None, stage_service=stage_service
    )

    assert result.total_rows == 2
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_get_stages_api_with_pagination(stage_service):
    """Test GET /stages endpoint with pagination."""
    for i in range(5):
        await stage_service.create_stage(
            StageCreate(title=f"Stage {i}", color="#FF0000")
        )

    result = await get_stages(
        page=1, page_size=2, search=None, stage_service=stage_service
    )

    assert result.total_rows == 5
    assert len(result.data) == 2
    assert result.total_pages == 3
    assert result.has_next is True


@pytest.mark.asyncio
async def test_get_stages_api_with_search(stage_service):
    """Test GET /stages endpoint with search."""
    await stage_service.create_stage(StageCreate(title="Under Review", color="#FF0000"))
    await stage_service.create_stage(StageCreate(title="Approved", color="#00FF00"))
    await stage_service.create_stage(
        StageCreate(title="Review Complete", color="#0000FF")
    )

    result = await get_stages(
        page=1, page_size=10, search="review", stage_service=stage_service
    )

    assert result.total_rows == 2
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_get_stage_api_success(stage_service):
    """Test GET /stages/{id} endpoint with valid ID."""
    created = await stage_service.create_stage(
        StageCreate(title="Test Stage", color="#FF9800")
    )

    result = await get_stage(stage_id=created.id, stage_service=stage_service)

    assert result.id == created.id
    assert result.title == "test stage"
    assert result.color == "#FF9800"


@pytest.mark.asyncio
async def test_get_stage_api_not_found(stage_service):
    """Test GET /stages/{id} endpoint with invalid ID."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await get_stage(stage_id=uuid4(), stage_service=stage_service)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_stage_api_success(stage_service):
    """Test POST /stages endpoint."""
    stage_data = StageCreate(title="New Stage", color="#4CAF50")

    result = await create_stage(stage_create=stage_data, stage_service=stage_service)

    assert result.title == "new stage"
    assert result.color == "#4CAF50"


@pytest.mark.asyncio
async def test_create_stage_api_duplicate_title(stage_service):
    """Test POST /stages endpoint with duplicate title."""
    stage_data = StageCreate(title="Duplicate", color="#FF0000")

    await stage_service.create_stage(stage_data)

    with pytest.raises(HTTPException) as exc_info:
        await create_stage(stage_create=stage_data, stage_service=stage_service)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_stage_api_success(stage_service):
    """Test PUT /stages/{id} endpoint."""
    created = await stage_service.create_stage(
        StageCreate(title="Original", color="#FF0000")
    )

    update_data = StageUpdate(title="Updated", color="#00FF00")
    result = await update_stage(
        stage_id=created.id, stage_update=update_data, stage_service=stage_service
    )

    assert result.id == created.id
    assert result.title == "updated"
    assert result.color == "#00FF00"


@pytest.mark.asyncio
async def test_update_stage_api_not_found(stage_service):
    """Test PUT /stages/{id} endpoint with invalid ID."""
    from uuid import uuid4

    update_data = StageUpdate(title="Updated", color="#00FF00")

    with pytest.raises(HTTPException) as exc_info:
        await update_stage(
            stage_id=uuid4(), stage_update=update_data, stage_service=stage_service
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_stage_api_duplicate_title(stage_service):
    """Test PUT /stages/{id} endpoint with duplicate title."""
    await stage_service.create_stage(StageCreate(title="Stage 1", color="#FF0000"))
    stage2 = await stage_service.create_stage(
        StageCreate(title="Stage 2", color="#00FF00")
    )

    update_data = StageUpdate(title="Stage 1", color="#0000FF")

    with pytest.raises(HTTPException) as exc_info:
        await update_stage(
            stage_id=stage2.id, stage_update=update_data, stage_service=stage_service
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_delete_stage_api_success(stage_service):
    """Test DELETE /stages/{id} endpoint."""
    created = await stage_service.create_stage(
        StageCreate(title="To Delete", color="#F44336")
    )

    result = await delete_stage(stage_id=created.id, stage_service=stage_service)

    assert "deleted successfully" in result.detail.lower()


@pytest.mark.asyncio
async def test_delete_stage_api_not_found(stage_service):
    """Test DELETE /stages/{id} endpoint with invalid ID."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await delete_stage(stage_id=uuid4(), stage_service=stage_service)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_stage_api_validates_hex_color():
    """Test POST /stages endpoint validates hex color format."""
    with pytest.raises(ValueError):
        StageCreate(title="Test", color="FF0000")

    with pytest.raises(ValueError):
        StageCreate(title="Test", color="#FF00")

    with pytest.raises(ValueError):
        StageCreate(title="Test", color="#GGGGGG")


@pytest.mark.asyncio
async def test_create_stage_api_converts_title_to_lowercase(stage_service):
    """Test POST /stages endpoint converts title to lowercase."""
    stage_data = StageCreate(title="UPPERCASE TITLE", color="#FF0000")

    result = await create_stage(stage_create=stage_data, stage_service=stage_service)

    assert result.title == "uppercase title"


@pytest.mark.asyncio
async def test_create_stage_api_normalizes_hex_color(stage_service):
    """Test POST /stages endpoint normalizes hex color to uppercase."""
    stage_data = StageCreate(title="Test", color="#ff9800")

    result = await create_stage(stage_create=stage_data, stage_service=stage_service)

    assert result.color == "#FF9800"
