"""add telegram_chat_id to users

Revision ID: a1b2c3d4e5f6
Revises: c6421b9a463c
Create Date: 2026-02-23 00:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "c6421b9a463c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True),
    )
    op.create_unique_constraint("uq_users_telegram_chat_id", "users", ["telegram_chat_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_telegram_chat_id", "users", type_="unique")
    op.drop_column("users", "telegram_chat_id")