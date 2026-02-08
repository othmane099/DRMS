import os
import sys

import pytest
from starlette import status

sys.path.append(f"{os.getcwd()}/src")
from auth.users.schemas import UserCreate, UserUpdate
from auth.users.service import UserServiceImpl
from schemas import Error, Message
from unit_of_work.fake_uow import FakeUnitOfWork


@pytest.fixture
def uow():
    """Provide a fake unit of work."""
    return FakeUnitOfWork()


@pytest.fixture
def user_service(uow):
    """Provide a user service with fake UoW."""
    return UserServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_create_user_success(user_service):
    """Test creating a new user successfully."""
    user_data = UserCreate(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        phone="1234567890",
        username="johndoe",
        password="SecurePass123",
        is_active=True,
    )

    result = await user_service.create_user(user_data)

    assert not isinstance(result, Error)
    assert result.first_name == "John"
    assert result.last_name == "Doe"
    assert result.username == "johndoe"
    assert result.email == "john@example.com"
    assert result.is_active is True
    # Password should be hashed, not plain
    assert result.password != "SecurePass123"


@pytest.mark.asyncio
async def test_create_user_duplicate_username(user_service):
    """Test creating a user with duplicate username fails."""
    user_data = UserCreate(
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        username="janedoe",
        password="SecurePass123",
        is_active=True,
    )

    await user_service.create_user(user_data)

    user_data2 = UserCreate(
        first_name="Janet",
        last_name="Doe",
        email="janet@example.com",
        username="janedoe",  # Same username
        password="SecurePass123",
        is_active=True,
    )
    result = await user_service.create_user(user_data2)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "username" in result.detail.lower()


@pytest.mark.asyncio
async def test_create_user_duplicate_email(user_service):
    """Test creating a user with duplicate email fails."""
    user_data = UserCreate(
        first_name="Bob",
        last_name="Smith",
        email="bob@example.com",
        username="bobsmith",
        password="SecurePass123",
        is_active=True,
    )

    await user_service.create_user(user_data)

    user_data2 = UserCreate(
        first_name="Robert",
        last_name="Smith",
        email="bob@example.com",  # Same email
        username="robertsmith",
        password="SecurePass123",
        is_active=True,
    )
    result = await user_service.create_user(user_data2)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_400_BAD_REQUEST
    assert "email" in result.detail.lower()


@pytest.mark.asyncio
async def test_get_user_by_id_success(user_service):
    """Test retrieving a user by ID."""
    user_data = UserCreate(
        first_name="Alice",
        last_name="Wonder",
        username="alicewonder",
        password="SecurePass123",
        is_active=True,
    )

    created = await user_service.create_user(user_data)
    assert not isinstance(created, Error)

    result = await user_service.get_user_by_id(created.id)

    assert not isinstance(result, Error)
    assert result.id == created.id
    assert result.username == "alicewonder"


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(user_service):
    """Test retrieving a non-existent user returns error."""
    from uuid import uuid4

    result = await user_service.get_user_by_id(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_user_by_username_success(user_service):
    """Test retrieving a user by username."""
    user_data = UserCreate(
        first_name="Charlie",
        last_name="Brown",
        username="charliebrown",
        password="SecurePass123",
        is_active=True,
    )

    await user_service.create_user(user_data)

    result = await user_service.get_user_by_username("charliebrown")

    assert not isinstance(result, Error)
    assert result.username == "charliebrown"


@pytest.mark.asyncio
async def test_update_user_success(user_service):
    """Test updating a user successfully."""
    user_data = UserCreate(
        first_name="David",
        last_name="Lee",
        username="davidlee",
        password="SecurePass123",
        is_active=True,
    )

    created = await user_service.create_user(user_data)
    assert not isinstance(created, Error)

    update_data = UserUpdate(
        first_name="David Updated",
        last_name="Lee Updated",
        email="david.updated@example.com",
        username="davidlee_updated",
        is_active=False,
    )

    result = await user_service.update_user(created.id, update_data)

    assert not isinstance(result, Error)
    assert result.first_name == "David Updated"
    assert result.last_name == "Lee Updated"
    assert result.username == "davidlee_updated"
    assert result.is_active is False


@pytest.mark.asyncio
async def test_update_user_not_found(user_service):
    """Test updating a non-existent user returns error."""
    from uuid import uuid4

    update_data = UserUpdate(
        first_name="Updated", last_name="User", username="updated", is_active=True
    )

    result = await user_service.update_user(uuid4(), update_data)

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_user_success(user_service):
    """Test deleting a user (soft delete)."""
    user_data = UserCreate(
        first_name="Temp",
        last_name="User",
        username="tempuser",
        password="SecurePass123",
        is_active=True,
    )

    created = await user_service.create_user(user_data)
    assert not isinstance(created, Error)

    result = await user_service.delete_user(created.id)

    assert isinstance(result, Message)
    assert "deleted successfully" in result.detail.lower()

    get_result = await user_service.get_user_by_id(created.id)
    assert isinstance(get_result, Error)


@pytest.mark.asyncio
async def test_delete_user_not_found(user_service):
    """Test deleting a non-existent user returns error."""
    from uuid import uuid4

    result = await user_service.delete_user(uuid4())

    assert isinstance(result, Error)
    assert result.code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_all_users_paginated(user_service):
    """Test retrieving paginated users."""
    for i in range(8):
        user_data = UserCreate(
            first_name=f"User{i}",
            last_name=f"Last{i}",
            username=f"user{i:02d}",
            password="SecurePass123",
            is_active=True,
        )
        await user_service.create_user(user_data)

    result = await user_service.get_all_users_paginated(page=1, page_size=5)

    assert not isinstance(result, Error)
    assert result.current_page == 1
    assert result.page_size == 5
    assert len(result.data) == 5
    assert result.total_rows == 8
    assert result.total_pages == 2
    assert result.has_next is True
    assert result.has_previous is False
