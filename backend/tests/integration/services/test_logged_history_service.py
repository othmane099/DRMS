from datetime import datetime, timedelta

import pytest
import pytz
from passlib.handlers.pbkdf2 import pbkdf2_sha256

from auth.logged_histories.service import LoggedHistoryServiceImpl
from auth.models import LoggedHistory, LoggedHistoryType, User
from db import default_session_factory
from unit_of_work.uow import UnitOfWorkImpl


@pytest.fixture
def service():
    uow = UnitOfWorkImpl(session_factory=default_session_factory)
    return LoggedHistoryServiceImpl(unit_of_work=uow)


async def _create_user(
    first_name: str = "Test", last_name: str = "User", username: str = "test_lh_user"
) -> User:
    async with default_session_factory() as session:
        hashed_password = pbkdf2_sha256.hash("TestPassword123")
        user = User(
            first_name=first_name,
            last_name=last_name,
            username=username,
            password=hashed_password,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _seed_logged_history(
    count: int = 3,
    user_id=None,
    type_: LoggedHistoryType = LoggedHistoryType.LOGIN,
    base_date: datetime | None = None,
    details: dict | None = None,
    ip: str = "127.0.0.1",
):
    if base_date is None:
        base_date = datetime.now(pytz.utc)
    async with default_session_factory() as session:
        for i in range(count):
            lh = LoggedHistory(
                user_id=user_id,
                ip=ip,
                date=base_date - timedelta(hours=i),
                details=details if details is not None else {"index": i},
                type=type_,
            )
            session.add(lh)
        await session.commit()


@pytest.mark.asyncio
async def test_returns_empty_when_no_entries(service):
    """Service returns empty paginated response when no logged histories exist."""
    result = await service.get_all_logged_histories_paginated(page=1, page_size=20)

    assert result.total_rows == 0
    assert result.data == []
    assert result.current_page == 1
    assert result.total_pages == 0
    assert result.has_next is False
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_returns_seeded_entries(service):
    """Service returns all seeded logged history entries."""
    await _seed_logged_history(count=3)

    result = await service.get_all_logged_histories_paginated(page=1, page_size=20)

    assert result.total_rows == 3
    assert len(result.data) == 3


@pytest.mark.asyncio
async def test_pagination_page_size(service):
    """Service respects page_size and returns correct total_pages."""
    await _seed_logged_history(count=5)

    result = await service.get_all_logged_histories_paginated(page=1, page_size=2)

    assert result.page_size == 2
    assert len(result.data) == 2
    assert result.total_rows == 5
    assert result.total_pages == 3
    assert result.has_next is True
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_pagination_second_page(service):
    """Service returns correct entries and state for second page."""
    await _seed_logged_history(count=5)

    result = await service.get_all_logged_histories_paginated(page=2, page_size=2)

    assert result.current_page == 2
    assert len(result.data) == 2
    assert result.has_next is True
    assert result.has_previous is True


@pytest.mark.asyncio
async def test_pagination_last_page(service):
    """Service marks has_next as False on the last page."""
    await _seed_logged_history(count=3)

    result = await service.get_all_logged_histories_paginated(page=2, page_size=2)

    assert result.current_page == 2
    assert len(result.data) == 1
    assert result.has_next is False
    assert result.has_previous is True


@pytest.mark.asyncio
async def test_filter_by_user_id(service):
    """Service returns only entries matching the given user_id."""
    user = await _create_user(username="lh_filter_user")
    await _seed_logged_history(count=2, user_id=user.id)
    await _seed_logged_history(count=3)  # anonymous entries

    result = await service.get_all_logged_histories_paginated(
        page=1, page_size=20, user_id=user.id
    )

    assert result.total_rows == 2
    assert all(str(entry.user_id) == str(user.id) for entry in result.data)


@pytest.mark.asyncio
async def test_filter_by_type_login(service):
    """Service returns only LOGIN entries when type_filter is LOGIN."""
    await _seed_logged_history(count=3, type_=LoggedHistoryType.LOGIN)
    await _seed_logged_history(count=2, type_=LoggedHistoryType.FAILED_LOGIN)

    result = await service.get_all_logged_histories_paginated(
        page=1, page_size=20, type_filter=LoggedHistoryType.LOGIN
    )

    assert result.total_rows == 3
    assert all(entry.type == LoggedHistoryType.LOGIN for entry in result.data)


@pytest.mark.asyncio
async def test_filter_by_type_failed_login(service):
    """Service returns only FAILED_LOGIN entries when type_filter is FAILED_LOGIN."""
    await _seed_logged_history(count=2, type_=LoggedHistoryType.LOGIN)
    await _seed_logged_history(count=4, type_=LoggedHistoryType.FAILED_LOGIN)

    result = await service.get_all_logged_histories_paginated(
        page=1, page_size=20, type_filter=LoggedHistoryType.FAILED_LOGIN
    )

    assert result.total_rows == 4
    assert all(entry.type == LoggedHistoryType.FAILED_LOGIN for entry in result.data)


@pytest.mark.asyncio
async def test_filter_by_date_from(service):
    """Service returns only entries at or after date_from."""
    now = datetime.now(pytz.utc)
    await _seed_logged_history(count=1, base_date=now - timedelta(days=5))
    await _seed_logged_history(count=1, base_date=now - timedelta(hours=1))

    result = await service.get_all_logged_histories_paginated(
        page=1, page_size=20, date_from=now - timedelta(days=1)
    )

    assert result.total_rows == 1


@pytest.mark.asyncio
async def test_filter_by_date_to(service):
    """Service returns only entries at or before date_to."""
    now = datetime.now(pytz.utc)
    await _seed_logged_history(count=1, base_date=now - timedelta(days=5))
    await _seed_logged_history(count=1, base_date=now - timedelta(hours=1))

    result = await service.get_all_logged_histories_paginated(
        page=1, page_size=20, date_to=now - timedelta(days=2)
    )

    assert result.total_rows == 1


@pytest.mark.asyncio
async def test_filter_by_search(service):
    """Service returns only entries whose details match the search string."""
    await _seed_logged_history(count=1, details={"browser": "chrome"})
    await _seed_logged_history(count=1, details={"browser": "firefox"})

    result = await service.get_all_logged_histories_paginated(
        page=1, page_size=20, search="chrome"
    )

    assert result.total_rows == 1
    assert result.data[0].details == {"browser": "chrome"}


@pytest.mark.asyncio
async def test_user_name_is_populated_from_relationship(service):
    """Service populates user_name from the linked user's first and last name."""
    user = await _create_user(
        first_name="Alice", last_name="Smith", username="alice_lh_test"
    )
    await _seed_logged_history(count=1, user_id=user.id)

    result = await service.get_all_logged_histories_paginated(page=1, page_size=20)

    assert result.total_rows == 1
    assert result.data[0].user_name == "Alice Smith"


@pytest.mark.asyncio
async def test_user_name_is_none_for_anonymous_entry(service):
    """Service returns user_name as None when user_id is not set."""
    await _seed_logged_history(count=1)

    result = await service.get_all_logged_histories_paginated(page=1, page_size=20)

    assert result.total_rows == 1
    assert result.data[0].user_name is None


@pytest.mark.asyncio
async def test_deleted_entries_are_excluded(service):
    """Service excludes soft-deleted logged history entries."""
    now = datetime.now(pytz.utc)
    async with default_session_factory() as session:
        active = LoggedHistory(
            ip="1.1.1.1",
            date=now,
            details={},
            type=LoggedHistoryType.LOGIN,
        )
        deleted = LoggedHistory(
            ip="2.2.2.2",
            date=now,
            details={},
            type=LoggedHistoryType.LOGIN,
            deleted_at=now,
        )
        session.add(active)
        session.add(deleted)
        await session.commit()

    result = await service.get_all_logged_histories_paginated(page=1, page_size=20)

    assert result.total_rows == 1
    assert result.data[0].ip == "1.1.1.1"
