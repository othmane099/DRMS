import asyncio
import os
import sys
import uuid

from passlib.handlers.pbkdf2 import pbkdf2_sha256

sys.path.append(f"{os.getcwd()}/src")

import config
from auth.models import User
from configuration.models import *  # noqa: F403
from core.models import *  # noqa: F403
from db import async_session, engine


async def create_superuser():
    username = config.settings.FIRST_SUPERUSER_USERNAME
    password = config.settings.FIRST_SUPERUSER_PASSWORD

    hashed_password = pbkdf2_sha256.hash(password)

    async with async_session() as db:
        from sqlalchemy import select

        result = await db.execute(select(User).where(User.username == username))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            print(f"User '{username}' already exists")
            return

        superuser = User(
            id=uuid.uuid4(),
            first_name="super",
            last_name="user",
            username=username,
            password=hashed_password,
            is_active=True,
            is_superuser=True,
        )

        db.add(superuser)
        await db.commit()
        await db.refresh(superuser)

        print(f"Superuser {username} created successfully")


async def main():
    try:
        await create_superuser()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
