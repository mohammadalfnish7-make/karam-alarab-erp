"""Task followers.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "work_task_followers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["work_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "user_id", name="uq_work_task_followers_task_user"),
    )
    op.create_index("ix_work_task_followers_task_id", "work_task_followers", ["task_id"])
    op.create_index("ix_work_task_followers_user_id", "work_task_followers", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_work_task_followers_user_id", table_name="work_task_followers")
    op.drop_index("ix_work_task_followers_task_id", table_name="work_task_followers")
    op.drop_table("work_task_followers")
