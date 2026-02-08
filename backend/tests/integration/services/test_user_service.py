import os
import sys

import pytest
from sqlalchemy import select

sys.path.insert(0, f"{os.getcwd()}/src")

from auth.models import User  # noqa: E402
from auth.users.schemas import UserCreate, UserUpdate  # noqa: E402
from auth.users.service import UserServiceImpl  # noqa: E402
from db import default_session_factory  # noqa: E402
from schemas import Error  # noqa: E402
from unit_of_work.uow import UnitOfWorkImpl  # noqa: E402


@pytest.fixture
def user_service():
    """Provide user service with real database."""
    uow = UnitOfWorkImpl(session_factory=default_session_factory)
    return UserServiceImpl(unit_of_work=uow)


@pytest.mark.asyncio
async def test_create_user_commits_to_database(user_service):
    """Test that creating a user commits data to database."""
    user_data = UserCreate(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        username="johndoe",
        password="SecurePassword123",
        is_active=True,
    )

    result = await user_service.create_user(user_data)

    assert not isinstance(result, Error)
    assert result.id is not None

    async with default_session_factory() as session:
        stmt = select(User).where(User.id == result.id)
        db_result = await session.execute(stmt)
        db_user = db_result.scalar_one_or_none()

        assert db_user is not None
        assert db_user.first_name == "John"
        assert db_user.last_name == "Doe"
        assert db_user.username == "johndoe"
        assert db_user.email == "john.doe@example.com"
        assert db_user.password != "SecurePassword123"


@pytest.mark.asyncio
async def test_update_user_commits_to_database(user_service):
    """Test that updating a user commits changes to database."""
    user_data = UserCreate(
        first_name="Jane",
        last_name="Smith",
        username="janesmith",
        password="SecurePassword123",
        is_active=True,
    )
    created = await user_service.create_user(user_data)
    assert not isinstance(created, Error)

    update_data = UserUpdate(
        first_name="Janet",
        last_name="Smith-Jones",
        email="janet@example.com",
        username="janetjones",
        is_active=False,
    )
    result = await user_service.update_user(created.id, update_data)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(User).where(User.id == created.id)
        db_result = await session.execute(stmt)
        db_user = db_result.scalar_one_or_none()

        assert db_user is not None
        assert db_user.first_name == "Janet"
        assert db_user.last_name == "Smith-Jones"
        assert db_user.username == "janetjones"
        assert db_user.is_active is False


@pytest.mark.asyncio
async def test_delete_user_soft_deletes_in_database(user_service):
    """Test that deleting a user sets deleted_at in database."""
    user_data = UserCreate(
        first_name="Temp",
        last_name="User",
        username="tempuser",
        password="SecurePassword123",
        is_active=True,
    )
    created = await user_service.create_user(user_data)
    assert not isinstance(created, Error)

    result = await user_service.delete_user(created.id)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(User).where(User.id == created.id)
        db_result = await session.execute(stmt)
        db_user = db_result.scalar_one_or_none()

        assert db_user is not None
        assert db_user.deleted_at is not None


@pytest.mark.asyncio
async def test_password_is_hashed_in_database(user_service):
    """Test that passwords are hashed before storing."""
    user_data = UserCreate(
        first_name="Secure",
        last_name="User",
        username="secureuser",
        password="PlainTextPassword123",
        is_active=True,
    )

    result = await user_service.create_user(user_data)
    assert not isinstance(result, Error)

    async with default_session_factory() as session:
        stmt = select(User).where(User.id == result.id)
        db_result = await session.execute(stmt)
        db_user = db_result.scalar_one_or_none()

        assert db_user is not None
        assert db_user.password != "PlainTextPassword123"
        assert db_user.password.startswith("$pbkdf2-sha256$")
