import os
import sys

import pytest
from sqlalchemy import select

sys.path.insert(0, f"{os.getcwd()}/src")

from configuration.models import Category, Stage, Subcategory  # noqa: E402
from db import default_session_factory  # noqa: E402


async def create_test_data():
    """Helper to create test data (category, subcategory, stage, user)."""
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    async with default_session_factory() as session:
        # Create category
        category = Category(title="API Test Category")
        session.add(category)
        await session.flush()

        # Create subcategory
        subcategory = Subcategory(title="API Test Subcategory", category_id=category.id)
        session.add(subcategory)
        await session.flush()

        # Create stage
        stage = Stage(title="API Test Stage", color="#00FF00")
        session.add(stage)
        await session.flush()

        # Create assigned user
        user = User(
            first_name="Assigned",
            last_name="User",
            username="assigned_user_api_test",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.flush()

        await session.commit()

        return {
            "category_id": str(category.id),
            "subcategory_id": str(subcategory.id),
            "stage_id": str(stage.id),
            "user_id": str(user.id),
        }


@pytest.mark.asyncio
async def test_create_reminder_api_integration_success(
    client, superuser_token, user_with_documents_permissions
):
    """Integration test: POST /documents/{document_id}/reminders endpoint."""
    from uuid import uuid4

    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    # Create test data
    test_data = await create_test_data()

    # Create users to assign reminder to
    user1_id = uuid4()
    user2_id = uuid4()

    async with default_session_factory() as session:
        user1 = User(
            id=user1_id,
            first_name="Reminder",
            last_name="User1",
            username=f"reminderuser1_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        user2 = User(
            id=user2_id,
            first_name="Reminder",
            last_name="User2",
            username=f"reminderuser2_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user1)
        session.add(user2)
        await session.commit()

    # Create document
    document_data = {
        "name": f"Test Reminder Doc {uuid4()}",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    file_content = b"test document content"
    files = {"document": ("test.pdf", file_content, "application/pdf")}

    response = await client.post(
        "/api/v1/documents",
        data=document_data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert response.status_code == 200
    document_id = response.json()["id"]

    # Create reminder
    reminder_data = {
        "date": "2026-12-31",
        "time": "14:30:00",
        "subject": "Important Meeting",
        "message": "Don't forget the quarterly review meeting",
        "assign_user": [str(user1_id), str(user2_id)],
    }

    reminder_response = await client.post(
        f"/api/v1/documents/{document_id}/reminders",
        json=reminder_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert reminder_response.status_code == 201
    reminder = reminder_response.json()
    assert reminder["document_id"] == document_id
    assert reminder["subject"] == "Important Meeting"
    assert reminder["message"] == "Don't forget the quarterly review meeting"
    assert len(reminder["assigned_users"]) == 2

    # Cleanup
    await client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    async with default_session_factory() as session:
        user1 = (
            await session.execute(select(User).where(User.id == user1_id))
        ).scalar_one_or_none()
        if user1:
            await session.delete(user1)
        user2 = (
            await session.execute(select(User).where(User.id == user2_id))
        ).scalar_one_or_none()
        if user2:
            await session.delete(user2)
        await session.commit()


@pytest.mark.asyncio
async def test_update_reminder_api_integration_success(
    client, superuser_token, user_with_documents_permissions
):
    """Integration test: PUT /reminders/{reminder_id} endpoint."""
    from uuid import uuid4

    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    # Create test data
    test_data = await create_test_data()

    # Create users
    user1_id = uuid4()
    user2_id = uuid4()

    async with default_session_factory() as session:
        user1 = User(
            id=user1_id,
            first_name="Reminder",
            last_name="User1",
            username=f"reminderuser1_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        user2 = User(
            id=user2_id,
            first_name="Reminder",
            last_name="User2",
            username=f"reminderuser2_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user1)
        session.add(user2)
        await session.commit()

    # Create document
    document_data = {
        "name": f"Test Reminder Update Doc {uuid4()}",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    file_content = b"test document content"
    files = {"document": ("test.pdf", file_content, "application/pdf")}

    response = await client.post(
        "/api/v1/documents",
        data=document_data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert response.status_code == 200
    document_id = response.json()["id"]

    # Create reminder
    reminder_data = {
        "date": "2026-12-31",
        "time": "14:30",
        "subject": "Original Subject",
        "message": "Original message",
        "assign_user": [str(user1_id)],
    }

    create_response = await client.post(
        f"/api/v1/documents/{document_id}/reminders",
        json=reminder_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response.status_code == 201
    reminder_id = create_response.json()["id"]

    # Update reminder
    update_data = {
        "date": "2027-01-15",
        "time": "16:00:00",
        "subject": "Updated Subject",
        "message": "Updated message",
        "assign_user": [str(user2_id)],
    }

    update_response = await client.put(
        f"/api/v1/reminders/{reminder_id}",
        json=update_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert update_response.status_code == 200
    updated_reminder = update_response.json()
    assert updated_reminder["subject"] == "Updated Subject"
    assert updated_reminder["message"] == "Updated message"
    assert len(updated_reminder["assigned_users"]) == 1

    # Cleanup
    await client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    async with default_session_factory() as session:
        user1 = (
            await session.execute(select(User).where(User.id == user1_id))
        ).scalar_one_or_none()
        if user1:
            await session.delete(user1)
        user2 = (
            await session.execute(select(User).where(User.id == user2_id))
        ).scalar_one_or_none()
        if user2:
            await session.delete(user2)
        await session.commit()


@pytest.mark.asyncio
async def test_get_reminder_api_integration_success(
    client, superuser_token, user_with_documents_permissions
):
    """Integration test: GET /reminders/{reminder_id} endpoint."""
    from uuid import uuid4

    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    # Create test data
    test_data = await create_test_data()

    # Create user
    user_id = uuid4()

    async with default_session_factory() as session:
        user = User(
            id=user_id,
            first_name="Reminder",
            last_name="User",
            username=f"reminderuser_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

    # Create document
    document_data = {
        "name": f"Test Reminder Get Doc {uuid4()}",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    file_content = b"test document content"
    files = {"document": ("test.pdf", file_content, "application/pdf")}

    response = await client.post(
        "/api/v1/documents",
        data=document_data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert response.status_code == 200
    document_id = response.json()["id"]

    # Create reminder
    reminder_data = {
        "date": "2026-12-31",
        "time": "14:30",
        "subject": "Test Reminder",
        "message": "Test message",
        "assign_user": [str(user_id)],
    }

    create_response = await client.post(
        f"/api/v1/documents/{document_id}/reminders",
        json=reminder_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response.status_code == 201
    reminder_id = create_response.json()["id"]

    # Get reminder by ID
    get_response = await client.get(
        f"/api/v1/reminders/{reminder_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert get_response.status_code == 200
    reminder = get_response.json()
    assert reminder["id"] == reminder_id
    assert reminder["subject"] == "Test Reminder"

    # Cleanup
    await client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    async with default_session_factory() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if user:
            await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_get_document_reminders_api_integration_success(
    client, superuser_token, user_with_documents_permissions
):
    """Integration test: GET /documents/{document_id}/reminders endpoint."""
    from uuid import uuid4

    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    # Create test data
    test_data = await create_test_data()

    # Create user
    user_id = uuid4()

    async with default_session_factory() as session:
        user = User(
            id=user_id,
            first_name="Reminder",
            last_name="User",
            username=f"reminderuser_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

    # Create document
    document_data = {
        "name": f"Test Reminder List Doc {uuid4()}",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    file_content = b"test document content"
    files = {"document": ("test.pdf", file_content, "application/pdf")}

    response = await client.post(
        "/api/v1/documents",
        data=document_data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert response.status_code == 200
    document_id = response.json()["id"]

    # Create multiple reminders
    for i in range(3):
        reminder_data = {
            "date": "2026-12-31",
            "time": "14:30",
            "subject": f"Reminder {i + 1}",
            "message": f"Message {i + 1}",
            "assign_user": [str(user_id)],
        }

        await client.post(
            f"/api/v1/documents/{document_id}/reminders",
            json=reminder_data,
            headers={"X-Session-Key": user_with_documents_permissions},
        )

    # Get all reminders for document
    get_response = await client.get(
        f"/api/v1/documents/{document_id}/reminders",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert get_response.status_code == 200
    reminders = get_response.json()
    assert len(reminders) == 3

    # Cleanup
    await client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    async with default_session_factory() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if user:
            await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_get_all_reminders_paginated_api_integration_success(
    client, superuser_token, user_with_documents_permissions
):
    """Integration test: GET /reminders endpoint with pagination."""
    from uuid import uuid4

    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User

    # Create test data
    test_data = await create_test_data()

    # Create user
    user_id = uuid4()

    async with default_session_factory() as session:
        user = User(
            id=user_id,
            first_name="Reminder",
            last_name="User",
            username=f"reminderuser_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

    # Create document
    document_data = {
        "name": f"Test Reminder Pagination Doc {uuid4()}",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    file_content = b"test document content"
    files = {"document": ("test.pdf", file_content, "application/pdf")}

    response = await client.post(
        "/api/v1/documents",
        data=document_data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert response.status_code == 200
    document_id = response.json()["id"]

    # Create multiple reminders
    for i in range(5):
        reminder_data = {
            "date": "2026-12-31",
            "time": "14:30",
            "subject": f"Reminder {i + 1}",
            "message": f"Message {i + 1}",
            "assign_user": [str(user_id)],
        }

        await client.post(
            f"/api/v1/documents/{document_id}/reminders",
            json=reminder_data,
            headers={"X-Session-Key": user_with_documents_permissions},
        )

    # Get paginated reminders
    get_response = await client.get(
        "/api/v1/reminders?page=1&page_size=3",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert get_response.status_code == 200
    result = get_response.json()
    assert result["current_page"] == 1
    assert result["page_size"] == 3
    assert result["total_rows"] >= 5  # May have more from other tests

    # Cleanup
    await client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    async with default_session_factory() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if user:
            await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_delete_reminder_api_integration_success(
    client, superuser_token, user_with_documents_permissions
):
    """Integration test: DELETE /reminders/{reminder_id} endpoint."""
    from uuid import uuid4

    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    from auth.models import User
    from core.models import Reminder

    # Create test data
    test_data = await create_test_data()

    # Create user
    user_id = uuid4()

    async with default_session_factory() as session:
        user = User(
            id=user_id,
            first_name="Reminder",
            last_name="User",
            username=f"reminderuser_{uuid4()}",
            password=pbkdf2_sha256.hash("password"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

    # Create document
    document_data = {
        "name": f"Test Reminder Delete Doc {uuid4()}",
        "category_id": test_data["category_id"],
        "subcategory_id": test_data["subcategory_id"],
        "stage_id": test_data["stage_id"],
        "assigned_to": test_data["user_id"],
    }

    file_content = b"test document content"
    files = {"document": ("test.pdf", file_content, "application/pdf")}

    response = await client.post(
        "/api/v1/documents",
        data=document_data,
        files=files,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert response.status_code == 200
    document_id = response.json()["id"]

    # Create reminder
    reminder_data = {
        "date": "2026-12-31",
        "time": "14:30",
        "subject": "Test Reminder",
        "message": "Test message",
        "assign_user": [str(user_id)],
    }

    create_response = await client.post(
        f"/api/v1/documents/{document_id}/reminders",
        json=reminder_data,
        headers={"X-Session-Key": user_with_documents_permissions},
    )
    assert create_response.status_code == 201
    reminder_id = create_response.json()["id"]

    # Delete reminder
    delete_response = await client.delete(
        f"/api/v1/reminders/{reminder_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    assert delete_response.status_code == 200
    assert "deleted successfully" in delete_response.json()["detail"].lower()

    # Verify deletion in database
    async with default_session_factory() as session:
        from uuid import UUID

        db_reminder = await session.execute(
            select(Reminder).where(Reminder.id == UUID(reminder_id))
        )
        reminder = db_reminder.scalar_one_or_none()
        assert reminder is None

    # Cleanup
    await client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"X-Session-Key": user_with_documents_permissions},
    )

    async with default_session_factory() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if user:
            await session.delete(user)
        await session.commit()
