import asyncio
import os
import sys
import uuid

sys.path.append(f"{os.getcwd()}/src")

from db import async_session, engine

PERMISSIONS: dict[str, str] = {
    "categories.create": "Create Category",
    "categories.delete": "Delete Category",
    "categories.list": "List Categories",
    "categories.update": "Edit Category",
    "categories.view": "View Category",
    "comments.create": "Create Comment",
    "comments.create_my": "Create My Own Comment",
    "comments.list": "List Comments",
    "comments.list_my": "List My Own Comments",
    "documents.archive": "Archive Document",
    "documents.archive_my": "Archive My Own Document",
    "documents.create": "Create Document",
    "documents.create_version": "Create Document Version",
    "documents.create_version_my": "Create My Document Version",
    "documents.delete": "Delete Document",
    "documents.delete_my": "Delete My Own Document",
    "documents.download": "Download Document",
    "documents.download_my": "Download My Own Document",
    "documents.download_version": "Download Document Version",
    "documents.download_version_my": "Download My Document Version",
    "documents.chat": "Chat Document",
    "documents.chat_my": "Chat My Document",
    "documents.history": "View Document History",
    "documents.history_my": "View My Document History",
    "documents.list": "List Documents",
    "documents.list_my": "List My Own Documents",
    "documents.preview": "Preview Document",
    "documents.preview_my": "Preview My Own Document",
    "documents.preview_version": "Preview Document Version",
    "documents.preview_version_my": "Preview My Document Version",
    "documents.share": "Share Document",
    "documents.share_my": "Share My Own Document",
    "documents.update": "Edit Document",
    "documents.update_my": "Edit My Own Document",
    "documents.view": "View Document",
    "documents.view_my": "View My Own Document",
    "documents.view_version": "View Document Version",
    "documents.view_version_my": "View My Document Version",
    "documents.search": "Search Document",
    "documents.search_my": "Search My Document",
    "logged_histories.delete": "Delete Logged History",
    "logged_histories.view": "View Logged History",
    "permissions.list": "List Permissions",
    "reminders.create": "Create Reminder",
    "reminders.create_my": "Create My Own Reminder",
    "reminders.delete": "Delete Reminder",
    "reminders.delete_my": "Delete My Own Reminder",
    "reminders.list": "List Reminders",
    "reminders.list_my": "List My Own Reminders",
    "reminders.update": "Edit Reminder",
    "reminders.update_my": "Edit My Own Reminder",
    "reminders.view": "View Reminder",
    "reminders.view_my": "View My Own Reminder",
    "roles.assign_permissions": "Assign Role Permissions",
    "roles.create": "Create Role",
    "roles.delete": "Delete Role",
    "roles.list": "List Roles",
    "roles.update": "Edit Role",
    "roles.view": "View Role",
    "stages.create": "Create Stage",
    "stages.delete": "Delete Stage",
    "stages.list": "List Stages",
    "stages.update": "Edit Stage",
    "stages.view": "View Stage",
    "subcategories.create": "Create Subcategory",
    "subcategories.delete": "Delete Subcategory",
    "subcategories.list": "List Subcategories",
    "subcategories.update": "Edit Subcategory",
    "subcategories.view": "View Subcategory",
    "tags.create": "Create Tag",
    "tags.delete": "Delete Tag",
    "tags.list": "List Tags",
    "tags.update": "Edit Tag",
    "tags.view": "View Tag",
    "users.create": "Create User",
    "users.delete": "Delete User",
    "users.list": "List Users",
    "users.update": "Edit User",
    "users.view": "View User",
}


async def seed_permissions() -> None:
    async with async_session() as db:
        from sqlalchemy import text

        existing_codes_result = await db.execute(text("SELECT code FROM permissions"))
        existing_codes = {row[0] for row in existing_codes_result.fetchall()}

        to_create = [
            {"id": uuid.uuid4(), "name": name, "code": code, "is_active": True}
            for code, name in PERMISSIONS.items()
            if code not in existing_codes
        ]

        if not to_create:
            print("All permissions already exist")
            return

        insert_stmt = text("""
                           INSERT INTO permissions (id, name, code, is_active)
                           VALUES (:id, :name, :code, :is_active) ON CONFLICT (code) DO NOTHING
                           """)

        await db.execute(insert_stmt, to_create)
        await db.commit()

        print(f"Inserted {len(to_create)} permissions:")
        for perm in to_create:
            print(f"  - {perm['name']}")


async def main() -> None:
    try:
        await seed_permissions()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())