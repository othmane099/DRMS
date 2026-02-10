import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

sys.path.append(f"{os.getcwd()}/src")

from auth.logged_histories.schemas import LoggedHistoryCreate
from auth.logged_histories.service import LoggedHistoryServiceImpl
from auth.models import LoggedHistoryType
from schemas import Error
from unit_of_work.fake_uow import FakeUnitOfWork


@pytest.fixture
def uow():
    return FakeUnitOfWork()


@pytest.fixture
def service(uow):
    return LoggedHistoryServiceImpl(unit_of_work=uow)


async def _seed(uow, **kwargs) -> None:
    defaults = {
        "user_id": None,
        "ip": "127.0.0.1",
        "date": datetime.now(),
        "details": {"username": "testuser"},
        "type": LoggedHistoryType.LOGIN,
    }
    defaults.update(kwargs)
    await uow.logged_history_repository.create_logged_history(
        LoggedHistoryCreate(**defaults)
    )


@pytest.mark.asyncio
async def test_returns_empty_when_no_entries(service):
    result = await service.get_all_logged_histories_paginated(page=1, page_size=20)

    assert not isinstance(result, Error)
    assert result.data == []
    assert result.total_rows == 0
    assert result.total_pages == 0


@pytest.mark.asyncio
async def test_returns_entries(service, uow):
    await _seed(uow)
    await _seed(uow)

    result = await service.get_all_logged_histories_paginated(page=1, page_size=20)

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.total_rows == 2


@pytest.mark.asyncio
async def test_pagination_page_size(service, uow):
    for _ in range(5):
        await _seed(uow)

    result = await service.get_all_logged_histories_paginated(page=1, page_size=3)

    assert not isinstance(result, Error)
    assert len(result.data) == 3
    assert result.total_rows == 5
    assert result.total_pages == 2
    assert result.has_next is True
    assert result.has_previous is False


@pytest.mark.asyncio
async def test_pagination_second_page(service, uow):
    for _ in range(5):
        await _seed(uow)

    result = await service.get_all_logged_histories_paginated(page=2, page_size=3)

    assert not isinstance(result, Error)
    assert len(result.data) == 2
    assert result.has_next is False
    assert result.has_previous is True


@pytest.mark.asyncio
async def test_filter_by_user_id(service, uow):
    target_user = uuid4()
    other_user = uuid4()
    await _seed(uow, user_id=target_user)
    await _seed(uow, user_id=target_user)
    await _seed(uow, user_id=other_user)

    result = await service.get_all_logged_histories_paginated(
        page=1, page_size=20, user_id=target_user
    )

    assert not isinstance(result, Error)
    assert result.total_rows == 2
    assert all(entry.user_id == target_user for entry in result.data)


@pytest.mark.asyncio
async def test_filter_by_type(service, uow):
    await _seed(uow, type=LoggedHistoryType.LOGIN)
    await _seed(uow, type=LoggedHistoryType.LOGIN)
    await _seed(uow, type=LoggedHistoryType.FAILED_LOGIN)

    result = await service.get_all_logged_histories_paginated(
        page=1, page_size=20, type_filter=LoggedHistoryType.FAILED_LOGIN
    )

    assert not isinstance(result, Error)
    assert result.total_rows == 1
    assert result.data[0].type == LoggedHistoryType.FAILED_LOGIN


@pytest.mark.asyncio
async def test_filter_by_date_range(service, uow):
    now = datetime.now()
    await _seed(uow, date=now - timedelta(days=2))
    await _seed(uow, date=now)
    await _seed(uow, date=now + timedelta(days=2))

    result = await service.get_all_logged_histories_paginated(
        page=1,
        page_size=20,
        date_from=now - timedelta(hours=1),
        date_to=now + timedelta(hours=1),
    )

    assert not isinstance(result, Error)
    assert result.total_rows == 1


@pytest.mark.asyncio
async def test_filter_by_search(service, uow):
    await _seed(uow, details={"username": "alice"})
    await _seed(uow, details={"username": "bob"})

    result = await service.get_all_logged_histories_paginated(
        page=1, page_size=20, search="alice"
    )

    assert not isinstance(result, Error)
    assert result.total_rows == 1
    assert result.data[0].details == {"username": "alice"}


@pytest.mark.asyncio
async def test_results_ordered_by_date_descending(service, uow):
    now = datetime.now()
    await _seed(uow, date=now - timedelta(hours=2))
    await _seed(uow, date=now)
    await _seed(uow, date=now - timedelta(hours=1))

    result = await service.get_all_logged_histories_paginated(page=1, page_size=20)

    assert not isinstance(result, Error)
    dates = [entry.date for entry in result.data]
    assert dates == sorted(dates, reverse=True)
