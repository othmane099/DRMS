import os
import sys
from datetime import date
from uuid import uuid4

import pytest

sys.path.append(f"{os.getcwd()}/src")
from auth.models import User
from core.dashboard.api import get_dashboard
from core.dashboard.fakes import FakeDashboardService


@pytest.fixture
def dashboard_service():
    return FakeDashboardService()


@pytest.fixture
def mock_user():
    """Provide a mock user for testing."""
    user = User()
    user.id = uuid4()
    user.username = "test_user"
    user.is_active = True
    user.is_superuser = False
    return user


@pytest.mark.asyncio
async def test_get_dashboard_empty(dashboard_service, mock_user):
    """Test GET /dashboard returns all zeros when no data exists."""
    result = await get_dashboard(
        current_user=mock_user, dashboard_service=dashboard_service
    )

    assert result.total_user == 0
    assert result.my_total_document == 0
    assert result.total_document == 0
    assert result.my_today_document == 0
    assert result.today_document == 0
    assert result.total_category == 0
    assert result.my_total_reminder == 0
    assert result.total_reminder == 0
    assert result.my_today_reminder == 0
    assert result.today_reminder == 0
    assert result.document_by_category == []
    assert result.document_by_subcategory == []
    assert result.my_reminders == []
    assert result.reminders == []


@pytest.mark.asyncio
async def test_get_dashboard_with_counts(mock_user):
    """Test GET /dashboard returns correct count values."""
    service = FakeDashboardService()
    service.total_user = 5
    service.total_document = 12
    service.today_document = 3
    service.total_category = 4
    service.total_reminder = 7
    service.today_reminder = 2

    result = await get_dashboard(current_user=mock_user, dashboard_service=service)

    assert result.total_user == 5
    assert result.total_document == 12
    assert result.today_document == 3
    assert result.total_category == 4
    assert result.total_reminder == 7
    assert result.today_reminder == 2


@pytest.mark.asyncio
async def test_get_dashboard_document_by_category(mock_user):
    """Test GET /dashboard returns documents grouped by category."""
    service = FakeDashboardService()
    service.document_by_category = [
        ("contracts", 6),
        ("invoices", 4),
        ("reports", 2),
    ]

    result = await get_dashboard(current_user=mock_user, dashboard_service=service)

    assert len(result.document_by_category) == 3
    assert result.document_by_category[0].category == "contracts"
    assert result.document_by_category[0].count == 6
    assert result.document_by_category[1].category == "invoices"
    assert result.document_by_category[1].count == 4
    assert result.document_by_category[2].category == "reports"
    assert result.document_by_category[2].count == 2


@pytest.mark.asyncio
async def test_get_dashboard_document_by_subcategory(mock_user):
    """Test GET /dashboard returns documents grouped by subcategory."""
    service = FakeDashboardService()
    service.document_by_subcategory = [
        ("lease", 5),
        ("nda", 3),
    ]

    result = await get_dashboard(current_user=mock_user, dashboard_service=service)

    assert len(result.document_by_subcategory) == 2
    assert result.document_by_subcategory[0].subcategory == "lease"
    assert result.document_by_subcategory[0].count == 5
    assert result.document_by_subcategory[1].subcategory == "nda"
    assert result.document_by_subcategory[1].count == 3


@pytest.mark.asyncio
async def test_get_dashboard_reminders(mock_user):
    """Test GET /dashboard returns reminder events with correct fields."""
    id1 = uuid4()
    id2 = uuid4()
    service = FakeDashboardService()
    service.reminders = [
        (id1, "Contract renewal", date(2026, 2, 10), "09:00"),
        (id2, "Sign NDA", date(2026, 3, 5), "14:30"),
    ]

    result = await get_dashboard(current_user=mock_user, dashboard_service=service)

    assert len(result.reminders) == 2
    assert result.reminders[0].id == id1
    assert result.reminders[0].title == "Contract renewal"
    assert result.reminders[0].start == date(2026, 2, 10)
    assert result.reminders[0].time == "09:00"
    assert result.reminders[1].id == id2
    assert result.reminders[1].title == "Sign NDA"
    assert result.reminders[1].start == date(2026, 3, 5)
    assert result.reminders[1].time == "14:30"


@pytest.mark.asyncio
async def test_get_dashboard_full_response(mock_user):
    """Test GET /dashboard returns a fully populated response."""
    reminder_id = uuid4()
    service = FakeDashboardService()
    service.total_user = 10
    service.my_total_document = 15
    service.total_document = 25
    service.my_today_document = 2
    service.today_document = 4
    service.total_category = 3
    service.my_total_reminder = 5
    service.total_reminder = 8
    service.my_today_reminder = 1
    service.today_reminder = 1
    service.document_by_category = [("contracts", 15), ("invoices", 10)]
    service.document_by_subcategory = [("lease", 8), ("purchase", 7), ("nda", 10)]
    service.reminders = [
        (reminder_id, "Quarterly review", date(2026, 2, 28), "11:00"),
    ]

    result = await get_dashboard(current_user=mock_user, dashboard_service=service)

    assert result.total_user == 10
    assert result.total_document == 25
    assert result.today_document == 4
    assert result.total_category == 3
    assert result.total_reminder == 8
    assert result.today_reminder == 1
    assert len(result.document_by_category) == 2
    assert len(result.document_by_subcategory) == 3
    assert len(result.reminders) == 1
    assert result.reminders[0].id == reminder_id
    assert result.reminders[0].title == "Quarterly review"
