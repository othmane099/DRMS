import asyncio
import os
import sys
import uuid

sys.path.append(f"{os.getcwd()}/src")

from db import async_session, engine

TAGS = [
    "Urgent",
    "Confidential",
    "Public",
    "Internal",
    "Draft",
    "Final",
    "Reviewed",
    "Archived",
]

STAGES = [
    {"title": "Received", "color": "#3B82F6"},
    {"title": "In Review", "color": "#F59E0B"},
    {"title": "Approved", "color": "#10B981"},
    {"title": "Rejected", "color": "#EF4444"},
    {"title": "Archived", "color": "#6B7280"},
]

CATEGORIES = {
    "Financial Documents": [
        "Invoices",
        "Receipts",
        "Budget Reports",
        "Financial Statements",
        "Tax Documents",
    ],
    "Human Resources": [
        "Employee Contracts",
        "Leave Applications",
        "Performance Reviews",
        "Recruitment",
        "Training Materials",
    ],
    "Legal Documents": [
        "Contracts",
        "Agreements",
        "Policies",
        "Compliance Documents",
        "Legal Correspondence",
    ],
    "Administrative": [
        "Meeting Minutes",
        "Memos",
        "Reports",
        "Correspondence",
        "Procedures",
    ],
    "Technical Documents": [
        "Specifications",
        "Manuals",
        "Diagrams",
        "Documentation",
        "Technical Reports",
    ],
}

MY_PERMISSIONS = [
    "comments.create_my",
    "comments.list_my",
    "documents.archive_my",
    "documents.create_version_my",
    "documents.delete_my",
    "documents.download_my",
    "documents.download_version_my",
    "documents.history_my",
    "documents.list_my",
    "documents.preview_my",
    "documents.preview_version_my",
    "documents.share_my",
    "documents.update_my",
    "documents.view_my",
    "documents.view_version_my",
    "reminders.delete_my",
    "reminders.list_my",
    "reminders.update_my",
    "reminders.view_my",
]


async def seed_tags() -> None:
    async with async_session() as db:
        from sqlalchemy import text

        existing_tags_result = await db.execute(text("SELECT title FROM tags"))
        existing_tags = {row[0] for row in existing_tags_result.fetchall()}

        to_create = [
            {"id": uuid.uuid4(), "title": tag}
            for tag in TAGS
            if tag not in existing_tags
        ]

        if not to_create:
            print("All tags already exist")
            return

        insert_stmt = text("""
            INSERT INTO tags (id, title)
            VALUES (:id, :title) ON CONFLICT (title) DO NOTHING
        """)

        await db.execute(insert_stmt, to_create)
        await db.commit()

        print(f"Inserted {len(to_create)} tags:")
        for tag in to_create:
            print(f"  - {tag['title']}")


async def seed_stages() -> None:
    async with async_session() as db:
        from sqlalchemy import text

        existing_stages_result = await db.execute(text("SELECT title FROM stages"))
        existing_stages = {row[0] for row in existing_stages_result.fetchall()}

        to_create = [
            {"id": uuid.uuid4(), "title": stage["title"], "color": stage["color"]}
            for stage in STAGES
            if stage["title"] not in existing_stages
        ]

        if not to_create:
            print("All stages already exist")
            return

        insert_stmt = text("""
            INSERT INTO stages (id, title, color)
            VALUES (:id, :title, :color) ON CONFLICT (title) DO NOTHING
        """)

        await db.execute(insert_stmt, to_create)
        await db.commit()

        print(f"Inserted {len(to_create)} stages:")
        for stage in to_create:
            print(f"  - {stage['title']} ({stage['color']})")


async def seed_categories_and_subcategories() -> None:
    async with async_session() as db:
        from sqlalchemy import text

        existing_cats_result = await db.execute(text("SELECT id, title FROM categories"))
        existing_cats = {row[1]: row[0] for row in existing_cats_result.fetchall()}

        cats_to_create = [
            {"id": uuid.uuid4(), "title": cat}
            for cat in CATEGORIES.keys()
            if cat not in existing_cats
        ]

        if cats_to_create:
            insert_cat_stmt = text("""
                INSERT INTO categories (id, title)
                VALUES (:id, :title) ON CONFLICT (title) DO NOTHING
            """)
            await db.execute(insert_cat_stmt, cats_to_create)
            await db.commit()

            print(f"Inserted {len(cats_to_create)} categories:")
            for cat in cats_to_create:
                print(f"  - {cat['title']}")

            existing_cats_result = await db.execute(
                text("SELECT id, title FROM categories")
            )
            existing_cats = {
                row[1]: row[0] for row in existing_cats_result.fetchall()
            }
        else:
            print("All categories already exist")

        existing_subcats_result = await db.execute(
            text("SELECT title FROM subcategories")
        )
        existing_subcats = {row[0] for row in existing_subcats_result.fetchall()}

        # Create missing subcategories
        subcats_to_create = []
        for cat_title, subcats in CATEGORIES.items():
            cat_id = existing_cats.get(cat_title)
            if cat_id:
                for subcat in subcats:
                    if subcat not in existing_subcats:
                        subcats_to_create.append(
                            {
                                "id": uuid.uuid4(),
                                "title": subcat,
                                "category_id": cat_id,
                            }
                        )

        if subcats_to_create:
            insert_subcat_stmt = text("""
                INSERT INTO subcategories (id, title, category_id)
                VALUES (:id, :title, :category_id) ON CONFLICT (title) DO NOTHING
            """)
            await db.execute(insert_subcat_stmt, subcats_to_create)
            await db.commit()

            print(f"Inserted {len(subcats_to_create)} subcategories:")
            for subcat in subcats_to_create:
                print(f"  - {subcat['title']}")
        else:
            print("All subcategories already exist")


async def seed_roles() -> None:
    async with async_session() as db:
        from sqlalchemy import text

        all_perms_result = await db.execute(
            text("SELECT id, code FROM permissions WHERE is_active = true")
        )
        all_perms = {row[1]: row[0] for row in all_perms_result.fetchall()}

        if not all_perms:
            print("Warning: No permissions found. Please run seed_permissions.py first")
            return

        existing_roles_result = await db.execute(text("SELECT name FROM roles"))
        existing_roles = {row[0] for row in existing_roles_result.fetchall()}

        if "Manager" not in existing_roles:
            manager_id = uuid.uuid4()
            manager_data = {
                "id": manager_id,
                "name": "Manager",
                "description": "Full access to all system features",
                "is_active": True,
            }

            await db.execute(
                text("""
                    INSERT INTO roles (id, name, description, is_active)
                    VALUES (:id, :name, :description, :is_active)
                """),
                manager_data,
            )

            role_perms = [
                {"role_id": manager_id, "permission_id": perm_id}
                for perm_id in all_perms.values()
            ]

            await db.execute(
                text("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (:role_id, :permission_id)
                """),
                role_perms,
            )

            await db.commit()
            print(f"Created Manager role with {len(role_perms)} permissions")
        else:
            print("Manager role already exists")

        if "User" not in existing_roles:
            user_id = uuid.uuid4()
            user_data = {
                "id": user_id,
                "name": "User",
                "description": "Access to own documents and resources",
                "is_active": True,
            }

            await db.execute(
                text("""
                    INSERT INTO roles (id, name, description, is_active)
                    VALUES (:id, :name, :description, :is_active)
                """),
                user_data,
            )

            user_perms = [
                {"role_id": user_id, "permission_id": all_perms[code]}
                for code in MY_PERMISSIONS
                if code in all_perms
            ]

            if user_perms:
                await db.execute(
                    text("""
                        INSERT INTO role_permissions (role_id, permission_id)
                        VALUES (:role_id, :permission_id)
                    """),
                    user_perms,
                )

                await db.commit()
                print(f"Created User role with {len(user_perms)} permissions")
            else:
                print("Warning: No matching permissions found for User role")
        else:
            print("User role already exists")


async def main() -> None:
    try:
        print("=== Seeding Tags ===")
        await seed_tags()

        print("\n=== Seeding Stages ===")
        await seed_stages()

        print("\n=== Seeding Categories and Subcategories ===")
        await seed_categories_and_subcategories()

        print("\n=== Seeding Roles ===")
        await seed_roles()

        print("\n✓ Configuration seeding completed successfully!")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())