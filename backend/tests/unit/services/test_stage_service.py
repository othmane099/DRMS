import os
import sys

import pytest
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from configuration.stages.schemas import StageCreate, StageUpdate
from configuration.stages.service import StageServiceImpl
from schemas import Error, Message
from unit_of_work.fake_uow import FakeUnitOfWork


@pytest.fixture
def uow():
    """Provide a fake unit of work."""
    return FakeUnitOfWork()


@pytest.fixture
def stage_service(uow):
    """Provide a stage service with fake UoW."""
    return StageServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_create_stage_success(stage_service):
    """Test creating a new stage successfully."""
    stage_data = StageCreate(title="Under Review", color="#FF9800")

    result = await stage_service.create_stage(stage_data)

    assert not isinstance(result, Error)
    assert result.title == "under review"
    assert result.color == "#FF9800"


@pytest.mark.asyncio
async def test_create_stage_duplicate_title(stage_service):
    """Test creating a stage with duplicate title fails."""
    stage_data = StageCreate(title="Approved", color="#4CAF50")

    await stage_service.create_stage(stage_data)

    result = await stage_service.create_stage(stage_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_create_stage_duplicate_title_case_insensitive(stage_service):
    """Test creating a stage with duplicate title (case insensitive) fails."""
    stage_data1 = StageCreate(title="Pending", color="#FFC107")
    stage_data2 = StageCreate(title="PENDING", color="#FFC107")

    await stage_service.create_stage(stage_data1)

    result = await stage_service.create_stage(stage_data2)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_stage_by_id_success(stage_service):
    """Test retrieving a stage by ID."""
    stage_data = StageCreate(title="In Progress", color="#2196F3")

    created = await stage_service.create_stage(stage_data)
    assert not isinstance(created, Error)

    result = await stage_service.get_stage_by_id(created.id)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.title == "in progress"


@pytest.mark.asyncio
async def test_get_stage_by_id_not_found(stage_service):
    """Test retrieving a non-existent stage returns error."""
    from uuid import uuid4

    result = await stage_service.get_stage_by_id(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_update_stage_success(stage_service):
    """Test updating a stage successfully."""
    stage_data = StageCreate(title="Draft", color="#9E9E9E")
    created = await stage_service.create_stage(stage_data)
    assert not isinstance(created, Error)

    update_data = StageUpdate(title="Final Draft", color="#757575")
    result = await stage_service.update_stage(created.id, update_data)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.title == "final draft"
    assert result.color == "#757575"


@pytest.mark.asyncio
async def test_update_stage_not_found(stage_service):
    """Test updating a non-existent stage returns error."""
    from uuid import uuid4

    update_data = StageUpdate(title="Updated", color="#000000")
    result = await stage_service.update_stage(uuid4(), update_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_update_stage_duplicate_title(stage_service):
    """Test updating a stage with duplicate title fails."""
    stage1 = StageCreate(title="Stage One", color="#FF0000")
    stage2 = StageCreate(title="Stage Two", color="#00FF00")

    created1 = await stage_service.create_stage(stage1)
    created2 = await stage_service.create_stage(stage2)
    assert not isinstance(created1, Error)
    assert not isinstance(created2, Error)

    update_data = StageUpdate(title="Stage One", color="#0000FF")
    result = await stage_service.update_stage(created2.id, update_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in result.detail.lower()


@pytest.mark.asyncio
async def test_update_stage_same_title(stage_service):
    """Test updating a stage with the same title succeeds."""
    stage_data = StageCreate(title="Review", color="#FF9800")
    created = await stage_service.create_stage(stage_data)
    assert not isinstance(created, Error)

    update_data = StageUpdate(title="Review", color="#FFC107")
    result = await stage_service.update_stage(created.id, update_data)

    assert not isinstance(result, Error)
    assert result.color == "#FFC107"


@pytest.mark.asyncio
async def test_delete_stage_success(stage_service):
    """Test deleting a stage successfully."""
    stage_data = StageCreate(title="To Delete", color="#F44336")
    created = await stage_service.create_stage(stage_data)
    assert not isinstance(created, Error)

    result = await stage_service.delete_stage(created.id)

    assert isinstance(result, Message)
    assert "deleted successfully" in result.detail.lower()

    get_result = await stage_service.get_stage_by_id(created.id)
    assert isinstance(get_result, Error)
    assert get_result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_stage_not_found(stage_service):
    """Test deleting a non-existent stage returns error."""
    from uuid import uuid4

    result = await stage_service.delete_stage(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND
    assert "not found" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_all_stages_paginated(stage_service):
    """Test retrieving paginated stages."""
    await stage_service.create_stage(StageCreate(title="Stage A", color="#FF0000"))
    await stage_service.create_stage(StageCreate(title="Stage B", color="#00FF00"))
    await stage_service.create_stage(StageCreate(title="Stage C", color="#0000FF"))

    result = await stage_service.get_all_stages_paginated(page=1, page_size=2)

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 3
    assert result.total_pages == 2
    assert result.has_next is True
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_get_all_stages_paginated_with_search(stage_service):
    """Test retrieving paginated stages with search."""
    await stage_service.create_stage(StageCreate(title="Under Review", color="#FF0000"))
    await stage_service.create_stage(StageCreate(title="Approved", color="#00FF00"))
    await stage_service.create_stage(
        StageCreate(title="Review Complete", color="#0000FF")
    )

    result = await stage_service.get_all_stages_paginated(
        page=1, page_size=10, search="review"
    )

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 2
