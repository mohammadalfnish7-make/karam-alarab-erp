"""Task due date and priority columns.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-28

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("work_tasks", sa.Column("due_on", sa.Date(), nullable=True))
    op.add_column(
        "work_tasks",
        sa.Column(
            "priority",
            sa.String(length=16),
            nullable=False,
            server_default="normal",
        ),
    )
    op.create_index("ix_work_tasks_due_on", "work_tasks", ["due_on"])
    op.create_index("ix_work_tasks_priority", "work_tasks", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_work_tasks_priority", table_name="work_tasks")
    op.drop_index("ix_work_tasks_due_on", table_name="work_tasks")
    op.drop_column("work_tasks", "priority")
    op.drop_column("work_tasks", "due_on")
