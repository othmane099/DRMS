import os
import sys

import pytest
from sqlalchemy import select

sys.path.insert(0, f"{os.getcwd()}/src")

from configuration.models import Stage  # noqa: E402
from configuration.stages.schemas import StageCreate, StageUpdate  # noqa: E402
from configuration.stages.service import StageServiceImpl  # noqa: E402
from db import default_session_factory  # noqa: E402
from schemas import Error  # noqa: E402
from unit_of_work.uow import UnitOfWorkImpl  # noqa: E402


@pytest.fixture
def stage_service():
    """Provide stage service with real database."""
    uow = UnitOfWorkImpl(session_factory=default_session_factory)
    return StageServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_create_stage_commits_to_database(stage_service):
    """Test that creating a stage commits data to database."""
    stage_data = StageCreate(title="Under Review", color="#FF9800")

    result = await stage_service.create_stage(stage_data)

    assert not isinstance(result, Error)
    assert result.id is not None

    async with default_session_factory() as session:
        stmt = select(Stage).where(Stage.id == result.id)
        db_result = await session.execute(stmt)
        db_stage = db_result.scalar_one_or_none()

        assert db_stage is not None
        assert db_stage.title == "under review"
        assert db_stage.color == "#FF9800"


@pytest.mark.asyncio
async def test_create_stage_duplicate_title_fails(stage_service):
    """Test that creating a stage with duplicate title fails."""
    stage_data = StageCreate(title="Approved", color="#4CAF50")
    await stage_service.create_stage(stage_data)

    result = await stage_service.create_stage(stage_data)

    assert isinstance(result, Error)
    assert result.code == 400


@pytest.mark.asyncio
async def test_create_stage_case_insensitive_uniqueness(stage_service):
    """Test that title uniqueness is case-insensitive."""
    stage_data1 = StageCreate(title="Pending", color="#FFC107")
    await stage_service.create_stage(stage_data1)

    stage_data2 = StageCreate(title="PENDING", color="#FFC107")
    result = await stage_service.create_stage(stage_data2)

    assert isinstance(result, Error)
    assert result.code == 400


@pytest.mark.asyncio
async def test_get_stage_by_id_returns_from_database(stage_service):
    """Test that getting a stage by ID retrieves from database."""
    stage_data = StageCreate(title="In Progress", color="#2196F3")
    created = await stage_service.create_stage(stage_data)
    assert not isinstance(created, Error)

    result = await stage_service.get_stage_by_id(created.id)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.title == "in progress"


@pytest.mark.asyncio
async def test_update_stage_commits_to_database(stage_service):
    """Test that updating a stage commits changes to database."""
    stage_data = StageCreate(title="Draft", color="#9E9E9E")
    created = await stage_service.create_stage(stage_data)
    assert not isinstance(created, Error)

    update_data = StageUpdate(title="Final Draft", color="#757575")
    result = await stage_service.update_stage(created.id, update_data)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(Stage).where(Stage.id == created.id)
        db_result = await session.execute(stmt)
        db_stage = db_result.scalar_one_or_none()

        assert db_stage is not None
        assert db_stage.title == "final draft"
        assert db_stage.color == "#757575"


@pytest.mark.asyncio
async def test_update_stage_duplicate_title_fails(stage_service):
    """Test that updating a stage with duplicate title fails."""
    stage1 = StageCreate(title="Stage One", color="#FF0000")
    stage2 = StageCreate(title="Stage Two", color="#00FF00")

    created1 = await stage_service.create_stage(stage1)
    created2 = await stage_service.create_stage(stage2)
    assert not isinstance(created1, Error)
    assert not isinstance(created2, Error)

    update_data = StageUpdate(title="Stage One", color="#0000FF")
    result = await stage_service.update_stage(created2.id, update_data)

    assert isinstance(result, Error)
    assert result.code == 400


@pytest.mark.asyncio
async def test_update_stage_same_title_succeeds(stage_service):
    """Test that updating a stage with the same title succeeds."""
    stage_data = StageCreate(title="Review", color="#FF9800")
    created = await stage_service.create_stage(stage_data)
    assert not isinstance(created, Error)

    update_data = StageUpdate(title="Review", color="#FFC107")
    result = await stage_service.update_stage(created.id, update_data)

    assert not isinstance(result, Error)
    assert result.color == "#FFC107"


@pytest.mark.asyncio
async def test_delete_stage_hard_deletes_in_database(stage_service):
    """Test that deleting a stage removes it from database (hard delete)."""
    stage_data = StageCreate(title="To Delete", color="#F44336")
    created = await stage_service.create_stage(stage_data)
    assert not isinstance(created, Error)

    result = await stage_service.delete_stage(created.id)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(Stage).where(Stage.id == created.id)
        db_result = await session.execute(stmt)
        db_stage = db_result.scalar_one_or_none()

        assert db_stage is None


@pytest.mark.asyncio
async def test_get_all_stages_paginated_from_database(stage_service):
    """Test that getting paginated stages retrieves from database."""
    await stage_service.create_stage(StageCreate(title="Stage A", color="#FF0000"))
    await stage_service.create_stage(StageCreate(title="Stage B", color="#00FF00"))
    await stage_service.create_stage(StageCreate(title="Stage C", color="#0000FF"))

    result = await stage_service.get_all_stages_paginated(page=1, page_size=2)

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 3
    assert result.total_pages == 2


@pytest.mark.asyncio
async def test_get_all_stages_search_in_database(stage_service):
    """Test that searching stages works with database."""
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
