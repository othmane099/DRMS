import os
import sys
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

sys.path.insert(0, f"{os.getcwd()}/src")

from auth.logged_histories.api import get_logged_histories  # noqa: E402
from auth.logged_histories.fakes import FakeLoggedHistoryService  # noqa: E402
from auth.models import LoggedHistory, LoggedHistoryType  # noqa: E402


@pytest.fixture
def service():
    return FakeLoggedHistoryService()


def _seed(service: FakeLoggedHistoryService, **kwargs) -> LoggedHistory:
    defaults = {
        "user_id": None,
        "ip": "127.0.0.1",
        "date": datetime.now(),
        "details": {"username": "testuser"},
        "type": LoggedHistoryType.LOGIN,
    }
    defaults.update(kwargs)
    entry = LoggedHistory(id=uuid4(), created_at=datetime.now(), **defaults)
    service.logged_histories[UUID(str(entry.id))] = entry
    return entry


@pytest.mark.asyncio
async def test_returns_results(service):
    _seed(service)
    _seed(service)

    result = await get_logged_histories(
        page=1,
        page_size=20,
        user_id=None,
        type=None,
        date_from=None,
        date_to=None,
        search=None,
        logged_history_service=service,
    )

    assert len(result.data) == 2
    assert result.total_rows == 2


@pytest.mark.asyncio
async def test_returns_empty(service):
    result = await get_logged_histories(
        page=1,
        page_size=20,
        user_id=None,
        type=None,
        date_from=None,
        date_to=None,
        search=None,
        logged_history_service=service,
    )

    assert result.data == []
    assert result.total_rows == 0


@pytest.mark.asyncio
async def test_filter_by_user_id(service):
    target_user = uuid4()
    _seed(service, user_id=target_user)
    _seed(service, user_id=uuid4())

    result = await get_logged_histories(
        page=1,
        page_size=20,
        user_id=target_user,
        type=None,
        date_from=None,
        date_to=None,
        search=None,
        logged_history_service=service,
    )

    assert result.total_rows == 1
    assert result.data[0].user_id == target_user


@pytest.mark.asyncio
async def test_filter_by_type(service):
    _seed(service, type=LoggedHistoryType.LOGIN)
    _seed(service, type=LoggedHistoryType.FAILED_LOGIN)

    result = await get_logged_histories(
        page=1,
        page_size=20,
        user_id=None,
        type=LoggedHistoryType.FAILED_LOGIN,
        date_from=None,
        date_to=None,
        search=None,
        logged_history_service=service,
    )

    assert result.total_rows == 1
    assert result.data[0].type == LoggedHistoryType.FAILED_LOGIN


@pytest.mark.asyncio
async def test_filter_by_date_range(service):
    now = datetime.now()
    _seed(service, date=now - timedelta(days=2))
    _seed(service, date=now)
    _seed(service, date=now + timedelta(days=2))

    result = await get_logged_histories(
        page=1,
        page_size=20,
        user_id=None,
        type=None,
        date_from=now - timedelta(hours=1),
        date_to=now + timedelta(hours=1),
        search=None,
        logged_history_service=service,
    )

    assert result.total_rows == 1


@pytest.mark.asyncio
async def test_filter_by_search(service):
    _seed(service, details={"username": "alice"})
    _seed(service, details={"username": "bob"})

    result = await get_logged_histories(
        page=1,
        page_size=20,
        user_id=None,
        type=None,
        date_from=None,
        date_to=None,
        search="alice",
        logged_history_service=service,
    )

    assert result.total_rows == 1
    assert result.data[0].details == {"username": "alice"}
