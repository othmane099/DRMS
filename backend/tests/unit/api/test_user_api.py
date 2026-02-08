import os
import sys

import pytest
from fastapi import HTTPException
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from auth.users.api import (
    create_user,
    delete_user,
    get_user,
    get_users,
    update_user,
)
from auth.users.fakes import FakeUserService
from auth.users.schemas import UserCreate, UserUpdate


@pytest.fixture
def user_service():
    return FakeUserService()


@pytest.mark.asyncio
async def test_get_users_api(user_service):
    """Test GET /users endpoint."""
    await user_service.create_user(
        UserCreate(
            first_name="John",
            last_name="Doe",
            username="johndoe",
            password="pass123",
            is_active=True,
        )
    )
    await user_service.create_user(
        UserCreate(
            first_name="Jane",
            last_name="Doe",
            username="janedoe",
            password="pass123",
            is_active=True,
        )
    )

    result = await get_users(
        page=1,
        page_size=10,
        role_id=None,
        search=None,
        active=None,
        user_service=user_service,
    )

    assert result.current_page == 1
    assert result.total_rows == 2
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_get_user_api_success(user_service):
    """Test GET /users/{id} endpoint with valid ID."""
    created = await user_service.create_user(
        UserCreate(
            first_name="Test",
            last_name="User",
            username="testuser",
            password="pass123",
            is_active=True,
        )
    )

    result = await get_user(user_id=created.id, user_service=user_service)

    assert result.id == created.id
    assert result.username == "testuser"


@pytest.mark.asyncio
async def test_get_user_api_not_found(user_service):
    """Test GET /users/{id} endpoint with invalid ID."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await get_user(user_id=uuid4(), user_service=user_service)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_user_api_success(user_service):
    """Test POST /users endpoint."""
    user_data = UserCreate(
        first_name="New",
        last_name="User",
        email="new@example.com",
        username="newuser",
        password="pass123",
        is_active=True,
    )

    result = await create_user(user_create=user_data, user_service=user_service)

    assert result.first_name == "New"
    assert result.last_name == "User"
    assert result.username == "newuser"
    assert result.email == "new@example.com"
    assert result.is_active is True


@pytest.mark.asyncio
async def test_create_user_api_duplicate_username(user_service):
    """Test POST /users endpoint with duplicate username."""
    user_data = UserCreate(
        first_name="Duplicate",
        last_name="User",
        username="duplicateuser",
        password="pass123",
        is_active=True,
    )

    await user_service.create_user(user_data)

    user_data2 = UserCreate(
        first_name="Another",
        last_name="User",
        username="duplicateuser",  # Same username
        password="pass123",
        is_active=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_user(user_create=user_data2, user_service=user_service)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_user_api_success(user_service):
    """Test PUT /users/{id} endpoint."""
    created = await user_service.create_user(
        UserCreate(
            first_name="Old",
            last_name="Name",
            username="olduser",
            password="pass123",
            is_active=True,
        )
    )

    update_data = UserUpdate(
        first_name="New",
        last_name="Name",
        email="updated@example.com",
        username="newuser",
        is_active=False,
    )

    result = await update_user(
        user_id=created.id, user_update=update_data, user_service=user_service
    )

    assert result.first_name == "New"
    assert result.last_name == "Name"
    assert result.username == "newuser"
    assert result.is_active is False


@pytest.mark.asyncio
async def test_update_user_api_not_found(user_service):
    """Test PUT /users/{id} endpoint with invalid ID."""
    from uuid import uuid4

    update_data = UserUpdate(
        first_name="Update", last_name="User", username="updateuser", is_active=True
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_user(
            user_id=uuid4(), user_update=update_data, user_service=user_service
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_user_api_success(user_service):
    """Test DELETE /users/{id} endpoint."""
    created = await user_service.create_user(
        UserCreate(
            first_name="Delete",
            last_name="Me",
            username="deleteme",
            password="pass123",
            is_active=True,
        )
    )

    result = await delete_user(user_id=created.id, user_service=user_service)

    assert "deleted successfully" in result.detail.lower()


@pytest.mark.asyncio
async def test_delete_user_api_not_found(user_service):
    """Test DELETE /users/{id} endpoint with invalid ID."""
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc_info:
        await delete_user(user_id=uuid4(), user_service=user_service)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
