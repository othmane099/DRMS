from datetime import date, time

import pytest
from httpx import AsyncClient

from auth.models import User
from configuration.models import Category, Stage, Subcategory
from core.models import Document, Reminder
from db import default_session_factory


@pytest.mark.asyncio
async def test_get_dashboard_requires_authentication(client: AsyncClient):
    """Test GET /api/v1/dashboard returns 422 without session token."""
    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_dashboard_response_structure(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/dashboard response contains all required fields."""
    response = await client.get(
        "/api/v1/dashboard",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    required_fields = [
        "total_user",
        "total_document",
        "today_document",
        "total_category",
        "total_reminder",
        "today_reminder",
        "document_by_category",
        "document_by_subcategory",
        "reminders",
    ]
    for field in required_fields:
        assert field in data


@pytest.mark.asyncio
async def test_get_dashboard_empty(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/dashboard returns zeros on empty database."""
    response = await client.get(
        "/api/v1/dashboard",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_user"] == 0
    assert data["total_document"] == 0
    assert data["today_document"] == 0
    assert data["total_category"] == 0
    assert data["total_reminder"] == 0
    assert data["today_reminder"] == 0
    assert data["document_by_category"] == []
    assert data["document_by_subcategory"] == []
    assert data["reminders"] == []


@pytest.mark.asyncio
async def test_get_dashboard_accessible_without_specific_permissions(
    client: AsyncClient, user_without_permissions: str
):
    """Test GET /api/v1/dashboard is accessible by any authenticated user."""
    response = await client.get(
        "/api/v1/dashboard",
        headers={"X-Session-Key": user_without_permissions},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_dashboard_counts_categories_via_api(
    client: AsyncClient, superuser_token: str
):
    """Test dashboard total_category reflects categories created via API."""
    await client.post(
        "/api/v1/categories",
        json={"title": "Contracts"},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/categories",
        json={"title": "Invoices"},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.get(
        "/api/v1/dashboard",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    assert response.json()["total_category"] == 2


@pytest.mark.asyncio
async def test_get_dashboard_counts_users_excluding_superuser(
    client: AsyncClient, superuser_token: str
):
    """Test dashboard total_user excludes superusers and soft-deleted users."""
    async with default_session_factory() as session:
        session.add(
            User(
                first_name="Regular",
                last_name="One",
                username="regularone",
                password="hashed",
                is_active=True,
                is_superuser=False,
            )
        )
        session.add(
            User(
                first_name="Regular",
                last_name="Two",
                username="regulartwo",
                password="hashed",
                is_active=True,
                is_superuser=False,
            )
        )
        await session.commit()

    response = await client.get(
        "/api/v1/dashboard",
        headers={"X-Session-Key": superuser_token},
    )

    # superuser_token fixture creates a superuser — not counted
    assert response.status_code == 200
    assert response.json()["total_user"] == 2


@pytest.mark.asyncio
async def test_get_dashboard_documents_grouped_by_category(
    client: AsyncClient, superuser_token: str
):
    """Test dashboard document_by_category groups and orders by count descending."""
    async with default_session_factory() as session:
        cat_a = Category(title="alpha")
        cat_b = Category(title="beta")
        stage = Stage(title="Active", color="#0000FF")
        user = User(
            first_name="Doc",
            last_name="User",
            username="docuser",
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

        for i in range(3):
            session.add(
                Document(
                    name=f"Alpha {i}",
                    category_id=cat_a.id,
                    subcategory_id=sub_a.id,
                    stage_id=stage.id,
                    assigned_to=user.id,
                    created_by=user.id,
                )
            )
        session.add(
            Document(
                name="Beta 0",
                category_id=cat_b.id,
                subcategory_id=sub_b.id,
                stage_id=stage.id,
                assigned_to=user.id,
                created_by=user.id,
            )
        )
        await session.commit()

    response = await client.get(
        "/api/v1/dashboard",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["document_by_category"]) == 2
    assert data["document_by_category"][0]["category"] == "alpha"
    assert data["document_by_category"][0]["count"] == 3
    assert data["document_by_category"][1]["category"] == "beta"
    assert data["document_by_category"][1]["count"] == 1


@pytest.mark.asyncio
async def test_get_dashboard_reminders_with_event_data(
    client: AsyncClient, superuser_token: str
):
    """Test dashboard reminders contain correct event fields and are ordered by date."""
    today = date.today()

    async with default_session_factory() as session:
        category = Category(title="evtcat")
        stage = Stage(title="Open", color="#FF00FF")
        user = User(
            first_name="Evt",
            last_name="User",
            username="evtuser",
            password="hashed",
            is_active=True,
            is_superuser=False,
        )
        session.add_all([category, stage, user])
        await session.flush()

        subcategory = Subcategory(title="evtsub", category_id=category.id)
        session.add(subcategory)
        await session.flush()

        doc = Document(
            name="Event Doc",
            category_id=category.id,
            subcategory_id=subcategory.id,
            stage_id=stage.id,
            assigned_to=user.id,
            created_by=user.id,
        )
        session.add(doc)
        await session.flush()

        # Future reminder inserted first — should appear second in response
        session.add(
            Reminder(
                document_id=doc.id,
                date=date(2030, 12, 25),
                time=time(12, 0),
                subject="Christmas",
                message="msg",
                created_by=user.id,
            )
        )
        # Today's reminder inserted second — should appear first in response
        session.add(
            Reminder(
                document_id=doc.id,
                date=today,
                time=time(9, 30),
                subject="Morning standup",
                message="msg",
                created_by=user.id,
            )
        )
        await session.commit()

    response = await client.get(
        "/api/v1/dashboard",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_reminder"] == 2
    assert data["today_reminder"] == 1
    assert len(data["reminders"]) == 2

    # Ordered by date asc: today < 2030-12-25
    assert data["reminders"][0]["title"] == "Morning standup"
    assert data["reminders"][0]["time"] == "09:30"
    assert data["reminders"][0]["start"] == today.isoformat()
    assert "id" in data["reminders"][0]

    assert data["reminders"][1]["title"] == "Christmas"
    assert data["reminders"][1]["time"] == "12:00"
    assert data["reminders"][1]["start"] == "2030-12-25"
