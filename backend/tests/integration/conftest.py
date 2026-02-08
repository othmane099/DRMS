import os
import sys

sys.path.insert(0, f"{os.getcwd()}/src")

import pytest_asyncio  # noqa: E402

from auth.models import Permission  # noqa: E402
from db import Base, default_session_factory, engine  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def setup_and_cleanup_database():
    """Setup and cleanup database tables for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with default_session_factory() as session:
        permissions = [
            Permission(
                name="List Permissions", code="permissions.list", is_active=True
            ),
            Permission(name="List Roles", code="roles.list", is_active=True),
            Permission(name="View Role", code="roles.view", is_active=True),
            Permission(name="Create Role", code="roles.create", is_active=True),
            Permission(name="Update Role", code="roles.update", is_active=True),
            Permission(name="Delete Role", code="roles.delete", is_active=True),
            Permission(
                name="Assign Permissions to Role",
                code="roles.assign_permissions",
                is_active=True,
            ),
            Permission(name="List Users", code="users.list", is_active=True),
            Permission(name="View User", code="users.view", is_active=True),
            Permission(name="Create User", code="users.create", is_active=True),
            Permission(name="Update User", code="users.update", is_active=True),
            Permission(name="Delete User", code="users.delete", is_active=True),
            Permission(
                name="View Logged History",
                code="logged_histories.view",
                is_active=True,
            ),
            Permission(
                name="Delete Logged History",
                code="logged_histories.delete",
                is_active=True,
            ),
            Permission(name="List Stages", code="stages.list", is_active=True),
            Permission(name="View Stage", code="stages.view", is_active=True),
            Permission(name="Create Stage", code="stages.create", is_active=True),
            Permission(name="Update Stage", code="stages.update", is_active=True),
            Permission(name="Delete Stage", code="stages.delete", is_active=True),
            Permission(name="List Categories", code="categories.list", is_active=True),
            Permission(name="View Category", code="categories.view", is_active=True),
            Permission(
                name="Create Category", code="categories.create", is_active=True
            ),
            Permission(
                name="Update Category", code="categories.update", is_active=True
            ),
            Permission(
                name="Delete Category", code="categories.delete", is_active=True
            ),
            Permission(
                name="List Subcategories", code="subcategories.list", is_active=True
            ),
            Permission(
                name="View Subcategory", code="subcategories.view", is_active=True
            ),
            Permission(
                name="Create Subcategory", code="subcategories.create", is_active=True
            ),
            Permission(
                name="Update Subcategory", code="subcategories.update", is_active=True
            ),
            Permission(
                name="Delete Subcategory", code="subcategories.delete", is_active=True
            ),
            Permission(name="List Tags", code="tags.list", is_active=True),
            Permission(name="View Tag", code="tags.view", is_active=True),
            Permission(name="Create Tag", code="tags.create", is_active=True),
            Permission(name="Update Tag", code="tags.update", is_active=True),
            Permission(name="Delete Tag", code="tags.delete", is_active=True),
            Permission(name="Manage Documents", code="documents.list", is_active=True),
            Permission(name="Create Document", code="documents.create", is_active=True),
        ]
        session.add_all(permissions)
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
