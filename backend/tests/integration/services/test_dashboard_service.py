import os
import sys
from datetime import date, datetime, time

import pytest
import pytz

sys.path.insert(0, f"{os.getcwd()}/src")

from auth.models import User  # noqa: E402
from configuration.models import Category, Stage, Subcategory  # noqa: E402
from core.dashboard.service import DashboardServiceImpl  # noqa: E402
from core.models import Document, Reminder  # noqa: E402
from db import default_session_factory  # noqa: E402
from unit_of_work.uow import UnitOfWorkImpl  # noqa: E402


@pytest.fixture
def dashboard_service():
    """Provide dashboard service with real database."""
    uow = UnitOfWorkImpl(session_factory=default_session_factory)
    return DashboardServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_get_dashboard_empty(dashboard_service):
    """Test dashboard returns all zeros on empty database."""
    result = await dashboard_service.get_dashboard()

    assert result.total_user == 0
    assert result.total_document == 0
    assert result.today_document == 0
    assert result.total_category == 0
    assert result.total_reminder == 0
    assert result.today_reminder == 0
    assert result.document_by_category == []
    assert result.document_by_subcategory == []
    assert result.reminders == []


@pytest.mark.asyncio
async def test_get_dashboard_counts_users(dashboard_service):
    """Test dashboard counts only non-superuser, non-deleted users."""
    async with default_session_factory() as session:
        # 3 regular users — counted
        for i in range(3):
            session.add(
                User(
                    first_name=f"User{i}",
                    last_name="Test",
                    username=f"user{i}",
                    password="hashed",
                    is_active=True,
                    is_superuser=False,
                )
            )
        # Superuser — excluded
        session.add(
            User(
                first_name="Super",
                last_name="User",
                username="superuser",
                password="hashed",
                is_active=True,
                is_superuser=True,
            )
        )
        # Soft-deleted user — excluded
        session.add(
            User(
                first_name="Deleted",
                last_name="User",
                username="deleteduser",
                password="hashed",
                is_active=True,
                is_superuser=False,
                deleted_at=datetime.now(pytz.utc),
            )
        )
        await session.commit()

    result = await dashboard_service.get_dashboard()
    assert result.total_user == 3


@pytest.mark.asyncio
async def test_get_dashboard_counts_documents(dashboard_service):
    """Test dashboard total_document and today_document match documents created today."""
    async with default_session_factory() as session:
        category = Category(title="doccat")
        stage = Stage(title="Draft", color="#FF0000")
        user = User(
            first_name="Doc",
            last_name="User",
            username="docuser",
            password="hashed",
            is_active=True,
            is_superuser=False,
        )
        session.add_all([category, stage, user])
        await session.flush()

        subcategory = Subcategory(title="docsub", category_id=category.id)
        session.add(subcategory)
        await session.flush()

        for i in range(3):
            session.add(
                Document(
                    name=f"Doc {i}",
                    category_id=category.id,
                    subcategory_id=subcategory.id,
                    stage_id=stage.id,
                    assigned_to=user.id,
                    created_by=user.id,
                )
            )
        await session.commit()

    result = await dashboard_service.get_dashboard()
    assert result.total_document == 3
    assert result.today_document == 3


@pytest.mark.asyncio
async def test_get_dashboard_counts_categories(dashboard_service):
    """Test dashboard total_category counts all categories."""
    async with default_session_factory() as session:
        session.add_all(
            [
                Category(title="catone"),
                Category(title="cattwo"),
                Category(title="catthree"),
            ]
        )
        await session.commit()

    result = await dashboard_service.get_dashboard()
    assert result.total_category == 3


@pytest.mark.asyncio
async def test_get_dashboard_counts_reminders(dashboard_service):
    """Test dashboard total_reminder and today_reminder are correct."""
    today = date.today()

    async with default_session_factory() as session:
        category = Category(title="remcat")
        stage = Stage(title="Open", color="#00FF00")
        user = User(
            first_name="Rem",
            last_name="User",
            username="remuser",
            password="hashed",
            is_active=True,
            is_superuser=False,
        )
        session.add_all([category, stage, user])
        await session.flush()

        subcategory = Subcategory(title="remsub", category_id=category.id)
        session.add(subcategory)
        await session.flush()

        doc = Document(
            name="Reminder Doc",
            category_id=category.id,
            subcategory_id=subcategory.id,
            stage_id=stage.id,
            assigned_to=user.id,
            created_by=user.id,
        )
        session.add(doc)
        await session.flush()

        # 2 reminders dated today
        session.add(
            Reminder(
                document_id=doc.id,
                date=today,
                time=time(10, 0),
                subject="Today 1",
                message="msg",
                created_by=user.id,
            )
        )
        session.add(
            Reminder(
                document_id=doc.id,
                date=today,
                time=time(15, 0),
                subject="Today 2",
                message="msg",
                created_by=user.id,
            )
        )
        # 1 reminder in the future
        session.add(
            Reminder(
                document_id=doc.id,
                date=date(2030, 6, 15),
                time=time(9, 0),
                subject="Future",
                message="msg",
                created_by=user.id,
            )
        )
        await session.commit()

    result = await dashboard_service.get_dashboard()
    assert result.total_reminder == 3
    assert result.today_reminder == 2


@pytest.mark.asyncio
async def test_get_dashboard_documents_by_category(dashboard_service):
    """Test dashboard groups documents by category ordered by count descending."""
    async with default_session_factory() as session:
        cat_a = Category(title="alpha")
        cat_b = Category(title="beta")
        stage = Stage(title="Active", color="#0000FF")
        user = User(
            first_name="Cat",
            last_name="User",
            username="catuser",
            password="hashed",
            is_active=True,
            is_superuser=False,
        )
        session.add_all([cat_a, cat_b, stage, user])
        await session.flush()

        sub_a = Subcategory(title="sub alpha", category_id=cat_a.id)
        sub_b = Subcategory(title="sub beta", category_id=cat_b.id)
        session.add_all([sub_a, sub_b])
        await session.flush()

        for i in range(4):
            session.add(
                Document(
                    name=f"Alpha Doc {i}",
                    category_id=cat_a.id,
                    subcategory_id=sub_a.id,
                    stage_id=stage.id,
                    assigned_to=user.id,
                    created_by=user.id,
                )
            )
        for i in range(2):
            session.add(
                Document(
                    name=f"Beta Doc {i}",
                    category_id=cat_b.id,
                    subcategory_id=sub_b.id,
                    stage_id=stage.id,
                    assigned_to=user.id,
                    created_by=user.id,
                )
            )
        await session.commit()

    result = await dashboard_service.get_dashboard()
    assert len(result.document_by_category) == 2
    assert result.document_by_category[0].category == "alpha"
    assert result.document_by_category[0].count == 4
    assert result.document_by_category[1].category == "beta"
    assert result.document_by_category[1].count == 2


@pytest.mark.asyncio
async def test_get_dashboard_documents_by_subcategory(dashboard_service):
    """Test dashboard groups documents by subcategory ordered by count descending."""
    async with default_session_factory() as session:
        cat = Category(title="parent")
        stage = Stage(title="Review", color="#FFFF00")
        user = User(
            first_name="Sub",
            last_name="User",
            username="subuser",
            password="hashed",
            is_active=True,
            is_superuser=False,
        )
        session.add_all([cat, stage, user])
        await session.flush()

        sub_x = Subcategory(title="xray", category_id=cat.id)
        sub_y = Subcategory(title="yankee", category_id=cat.id)
        session.add_all([sub_x, sub_y])
        await session.flush()

        session.add(
            Document(
                name="Xray Doc",
                category_id=cat.id,
                subcategory_id=sub_x.id,
                stage_id=stage.id,
                assigned_to=user.id,
                created_by=user.id,
            )
        )
        for i in range(3):
            session.add(
                Document(
                    name=f"Yankee Doc {i}",
                    category_id=cat.id,
                    subcategory_id=sub_y.id,
                    stage_id=stage.id,
                    assigned_to=user.id,
                    created_by=user.id,
                )
            )
        await session.commit()

    result = await dashboard_service.get_dashboard()
    assert len(result.document_by_subcategory) == 2
    assert result.document_by_subcategory[0].subcategory == "yankee"
    assert result.document_by_subcategory[0].count == 3
    assert result.document_by_subcategory[1].subcategory == "xray"
    assert result.document_by_subcategory[1].count == 1


@pytest.mark.asyncio
async def test_get_dashboard_reminders_ordered_by_date_and_time(dashboard_service):
    """Test dashboard reminders are sorted by date asc then time asc."""
    async with default_session_factory() as session:
        category = Category(title="ordercat")
        stage = Stage(title="Pending", color="#808080")
        user = User(
            first_name="Order",
            last_name="User",
            username="orderuser",
            password="hashed",
            is_active=True,
            is_superuser=False,
        )
        session.add_all([category, stage, user])
        await session.flush()

        subcategory = Subcategory(title="ordersub", category_id=category.id)
        session.add(subcategory)
        await session.flush()

        doc = Document(
            name="Order Doc",
            category_id=category.id,
            subcategory_id=subcategory.id,
            stage_id=stage.id,
            assigned_to=user.id,
            created_by=user.id,
        )
        session.add(doc)
        await session.flush()

        # Inserted in non-chronological order intentionally
        session.add(
            Reminder(
                document_id=doc.id,
                date=date(2030, 3, 1),
                time=time(10, 0),
                subject="March",
                message="msg",
                created_by=user.id,
            )
        )
        session.add(
            Reminder(
                document_id=doc.id,
                date=date(2030, 1, 15),
                time=time(14, 0),
                subject="Jan Afternoon",
                message="msg",
                created_by=user.id,
            )
        )
        session.add(
            Reminder(
                document_id=doc.id,
                date=date(2030, 1, 15),
                time=time(8, 0),
                subject="Jan Morning",
                message="msg",
                created_by=user.id,
            )
        )
        await session.commit()

    result = await dashboard_service.get_dashboard()
    assert len(result.reminders) == 3
    assert result.reminders[0].title == "Jan Morning"
    assert result.reminders[0].start == date(2030, 1, 15)
    assert result.reminders[0].time == "08:00"
    assert result.reminders[1].title == "Jan Afternoon"
    assert result.reminders[1].start == date(2030, 1, 15)
    assert result.reminders[1].time == "14:00"
    assert result.reminders[2].title == "March"
    assert result.reminders[2].start == date(2030, 3, 1)
    assert result.reminders[2].time == "10:00"
