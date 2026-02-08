import os
import sys

sys.path.insert(0, f"{os.getcwd()}/src")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

import main as app_main  # noqa: E402
from auth.models import (  # noqa: E402
    Permission,
    Role,
    User,  # noqa: E402
)
from auth.models import Session as SessionModel  # noqa: E402
from db import default_session_factory  # noqa: E402


@pytest_asyncio.fixture
async def client(setup_and_cleanup_database):
    """Provide HTTP client for testing API endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app_main.app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def superuser_token(client: AsyncClient):
    """Create a superuser and return auth token."""
    import secrets
    from datetime import datetime, timedelta

    import pytz
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    async with default_session_factory() as session:
        hashed_password = pbkdf2_sha256.hash("TestPassword123")
        user = User(
            first_name="Super",
            last_name="User",
            username="superuser_test",
            password=hashed_password,
            is_active=True,
            is_superuser=True,
        )
        session.add(user)
        await session.flush()

        token = secrets.token_urlsafe(32)
        user_session = SessionModel(
            user_id=user.id,
            token=token,
            expired_at=datetime.now(pytz.utc) + timedelta(hours=24),
            is_active=True,
        )
        session.add(user_session)
        await session.commit()

        return token


@pytest_asyncio.fixture
async def user_with_tags_permissions(client: AsyncClient):
    """Create a regular user with tags permissions and return auth token."""
    import secrets
    from datetime import datetime, timedelta

    import pytz
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    async with default_session_factory() as session:
        # Get tags permissions
        stmt = select(Permission).where(
            Permission.code.in_(
                [
                    "tags.list",
                    "tags.view",
                    "tags.create",
                    "tags.update",
                    "tags.delete",
                ]
            )
        )
        result = await session.execute(stmt)
        permissions = list(result.scalars().all())

        # Create role with tags permissions
        role = Role(name="Tags Manager", is_active=True)
        role.permissions = permissions
        session.add(role)
        await session.flush()

        # Create user with tags role
        hashed_password = pbkdf2_sha256.hash("TestPassword123")
        user = User(
            first_name="Tags",
            last_name="User",
            username="tags_user_test",
            password=hashed_password,
            is_active=True,
            is_superuser=False,
            role_id=role.id,
        )
        session.add(user)
        await session.flush()

        # Create session token
        token = secrets.token_urlsafe(32)
        user_session = SessionModel(
            user_id=user.id,
            token=token,
            expired_at=datetime.now(pytz.utc) + timedelta(hours=24),
            is_active=True,
        )
        session.add(user_session)
        await session.commit()

        return token


@pytest_asyncio.fixture
async def user_without_permissions(client: AsyncClient):
    """Create a regular user without any permissions and return auth token."""
    import secrets
    from datetime import datetime, timedelta

    import pytz
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    async with default_session_factory() as session:
        # Create role with no permissions
        role = Role(name="No Permissions", is_active=True)
        session.add(role)
        await session.flush()

        # Create user with no permissions
        hashed_password = pbkdf2_sha256.hash("TestPassword123")
        user = User(
            first_name="No",
            last_name="Permissions",
            username="no_perms_user_test",
            password=hashed_password,
            is_active=True,
            is_superuser=False,
            role_id=role.id,
        )
        session.add(user)
        await session.flush()

        # Create session token
        token = secrets.token_urlsafe(32)
        user_session = SessionModel(
            user_id=user.id,
            token=token,
            expired_at=datetime.now(pytz.utc) + timedelta(hours=24),
            is_active=True,
        )
        session.add(user_session)
        await session.commit()

        return token


@pytest_asyncio.fixture
async def user_with_stages_permissions(client: AsyncClient):
    """Create a regular user with stages permissions and return auth token."""
    import secrets
    from datetime import datetime, timedelta

    import pytz
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    async with default_session_factory() as session:
        stmt = select(Permission).where(
            Permission.code.in_(
                [
                    "stages.list",
                    "stages.view",
                    "stages.create",
                    "stages.update",
                    "stages.delete",
                ]
            )
        )
        result = await session.execute(stmt)
        permissions = list(result.scalars().all())

        role = Role(name="Stages Manager", is_active=True)
        role.permissions = permissions
        session.add(role)
        await session.flush()

        hashed_password = pbkdf2_sha256.hash("TestPassword123")
        user = User(
            first_name="Stages",
            last_name="User",
            username="stages_user_test",
            password=hashed_password,
            is_active=True,
            is_superuser=False,
            role_id=role.id,
        )
        session.add(user)
        await session.flush()

        token = secrets.token_urlsafe(32)
        user_session = SessionModel(
            user_id=user.id,
            token=token,
            expired_at=datetime.now(pytz.utc) + timedelta(hours=24),
            is_active=True,
        )
        session.add(user_session)
        await session.commit()

        return token


@pytest_asyncio.fixture
async def user_with_categories_permissions(client: AsyncClient):
    """Create a regular user with categories permissions and return auth token."""
    import secrets
    from datetime import datetime, timedelta

    import pytz
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    async with default_session_factory() as session:
        stmt = select(Permission).where(
            Permission.code.in_(
                [
                    "categories.list",
                    "categories.view",
                    "categories.create",
                    "categories.update",
                    "categories.delete",
                ]
            )
        )
        result = await session.execute(stmt)
        permissions = list(result.scalars().all())

        role = Role(name="Categories Manager", is_active=True)
        role.permissions = permissions
        session.add(role)
        await session.flush()

        hashed_password = pbkdf2_sha256.hash("TestPassword123")
        user = User(
            first_name="Categories",
            last_name="User",
            username="categories_user_test",
            password=hashed_password,
            is_active=True,
            is_superuser=False,
            role_id=role.id,
        )
        session.add(user)
        await session.flush()

        token = secrets.token_urlsafe(32)
        user_session = SessionModel(
            user_id=user.id,
            token=token,
            expired_at=datetime.now(pytz.utc) + timedelta(hours=24),
            is_active=True,
        )
        session.add(user_session)
        await session.commit()

        return token


@pytest_asyncio.fixture
async def user_with_subcategories_permissions(client: AsyncClient):
    """Create a regular user with subcategories permissions and return auth token."""
    import secrets
    from datetime import datetime, timedelta

    import pytz
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    async with default_session_factory() as session:
        stmt = select(Permission).where(
            Permission.code.in_(
                [
                    "subcategories.list",
                    "subcategories.view",
                    "subcategories.create",
                    "subcategories.update",
                    "subcategories.delete",
                ]
            )
        )
        result = await session.execute(stmt)
        permissions = list(result.scalars().all())

        role = Role(name="Subcategories Manager", is_active=True)
        role.permissions = permissions
        session.add(role)
        await session.flush()

        hashed_password = pbkdf2_sha256.hash("TestPassword123")
        user = User(
            first_name="Subcategories",
            last_name="User",
            username="subcategories_user_test",
            password=hashed_password,
            is_active=True,
            is_superuser=False,
            role_id=role.id,
        )
        session.add(user)
        await session.flush()

        token = secrets.token_urlsafe(32)
        user_session = SessionModel(
            user_id=user.id,
            token=token,
            expired_at=datetime.now(pytz.utc) + timedelta(hours=24),
            is_active=True,
        )
        session.add(user_session)
        await session.commit()

        return token


@pytest_asyncio.fixture
async def user_with_users_permissions(client: AsyncClient):
    """Create a regular user with users permissions and return auth token."""
    import secrets
    from datetime import datetime, timedelta

    import pytz
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    async with default_session_factory() as session:
        stmt = select(Permission).where(
            Permission.code.in_(
                [
                    "users.list",
                    "users.view",
                    "users.create",
                    "users.update",
                    "users.delete",
                ]
            )
        )
        result = await session.execute(stmt)
        permissions = list(result.scalars().all())

        role = Role(name="Users Manager", is_active=True)
        role.permissions = permissions
        session.add(role)
        await session.flush()

        hashed_password = pbkdf2_sha256.hash("TestPassword123")
        user = User(
            first_name="Users",
            last_name="Manager",
            username="users_manager_test",
            password=hashed_password,
            is_active=True,
            is_superuser=False,
            role_id=role.id,
        )
        session.add(user)
        await session.flush()

        token = secrets.token_urlsafe(32)
        user_session = SessionModel(
            user_id=user.id,
            token=token,
            expired_at=datetime.now(pytz.utc) + timedelta(hours=24),
            is_active=True,
        )
        session.add(user_session)
        await session.commit()

        return token


@pytest_asyncio.fixture
async def user_with_roles_permissions(client: AsyncClient):
    """Create a regular user with roles permissions and return auth token."""
    import secrets
    from datetime import datetime, timedelta

    import pytz
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    async with default_session_factory() as session:
        stmt = select(Permission).where(
            Permission.code.in_(
                [
                    "roles.list",
                    "roles.view",
                    "roles.create",
                    "roles.update",
                    "roles.delete",
                    "roles.assign_permissions",
                ]
            )
        )
        result = await session.execute(stmt)
        permissions = list(result.scalars().all())

        role = Role(name="Roles Manager", is_active=True)
        role.permissions = permissions
        session.add(role)
        await session.flush()

        hashed_password = pbkdf2_sha256.hash("TestPassword123")
        user = User(
            first_name="Roles",
            last_name="Manager",
            username="roles_manager_test",
            password=hashed_password,
            is_active=True,
            is_superuser=False,
            role_id=role.id,
        )
        session.add(user)
        await session.flush()

        token = secrets.token_urlsafe(32)
        user_session = SessionModel(
            user_id=user.id,
            token=token,
            expired_at=datetime.now(pytz.utc) + timedelta(hours=24),
            is_active=True,
        )
        session.add(user_session)
        await session.commit()

        return token


@pytest_asyncio.fixture
async def user_with_permissions_permissions(client: AsyncClient):
    """Create a regular user with permissions permissions and return auth token."""
    import secrets
    from datetime import datetime, timedelta

    import pytz
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    async with default_session_factory() as session:
        stmt = select(Permission).where(Permission.code == "permissions.list")
        result = await session.execute(stmt)
        permissions = list(result.scalars().all())

        role = Role(name="Permissions Viewer", is_active=True)
        role.permissions = permissions
        session.add(role)
        await session.flush()

        hashed_password = pbkdf2_sha256.hash("TestPassword123")
        user = User(
            first_name="Permissions",
            last_name="Viewer",
            username="permissions_viewer_test",
            password=hashed_password,
            is_active=True,
            is_superuser=False,
            role_id=role.id,
        )
        session.add(user)
        await session.flush()

        token = secrets.token_urlsafe(32)
        user_session = SessionModel(
            user_id=user.id,
            token=token,
            expired_at=datetime.now(pytz.utc) + timedelta(hours=24),
            is_active=True,
        )
        session.add(user_session)
        await session.commit()

        return token


@pytest_asyncio.fixture
async def user_with_documents_permissions(client: AsyncClient):
    """Create a regular user with documents permissions and return auth token."""
    import secrets
    from datetime import datetime, timedelta

    import pytz
    from passlib.handlers.pbkdf2 import pbkdf2_sha256

    async with default_session_factory() as session:
        # Check which permissions exist and create missing ones
        permission_codes = [
            "documents.list",
            "documents.create",
            "documents.delete",
            "documents.view",
            "documents.view_version",
            "documents.create_version",
            "documents.archive",
            "comments.create",
            "comments.list",
            "documents.share",
            "documents.delete_share",
            "reminders.create",
            "reminders.view",
            "reminders.update",
            "reminders.delete",
            "reminders.list",
            "documents.preview_version",
            "documents.download",
        ]

        stmt = select(Permission).where(Permission.code.in_(permission_codes))
        result = await session.execute(stmt)
        existing_permissions = list(result.scalars().all())
        existing_codes = {p.code for p in existing_permissions}

        # Create missing permissions
        for code in permission_codes:
            if code not in existing_codes:
                new_permission = Permission(
                    code=code, name=code.replace(".", " ").title()
                )
                session.add(new_permission)

        await session.flush()

        # Re-fetch all permissions
        stmt = select(Permission).where(Permission.code.in_(permission_codes))
        result = await session.execute(stmt)
        permissions = list(result.scalars().all())

        role = Role(name="Documents Manager", is_active=True)
        role.permissions = permissions
        session.add(role)
        await session.flush()

        hashed_password = pbkdf2_sha256.hash("TestPassword123")
        user = User(
            first_name="Documents",
            last_name="Manager",
            username="documents_manager_test",
            password=hashed_password,
            is_active=True,
            is_superuser=False,
            role_id=role.id,
        )
        session.add(user)
        await session.flush()

        token = secrets.token_urlsafe(32)
        user_session = SessionModel(
            user_id=user.id,
            token=token,
            expired_at=datetime.now(pytz.utc) + timedelta(hours=24),
            is_active=True,
        )
        session.add(user_session)
        await session.commit()

        return token
