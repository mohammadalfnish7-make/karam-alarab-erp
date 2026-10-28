"""Human task references per type (type-name-N).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-28

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "work_task_type_sequences" not in tables:
        op.create_table(
            "work_task_type_sequences",
            sa.Column("task_type_id", sa.Uuid(), nullable=False),
            sa.Column("next_value", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(
                ["task_type_id"], ["work_task_types.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("task_type_id"),
        )

    task_cols = {c["name"] for c in inspector.get_columns("work_tasks")}
    if "reference" not in task_cols:
        op.add_column(
            "work_tasks",
            sa.Column(
                "reference", sa.String(length=160), nullable=False, server_default=""
            ),
        )
    if "sequence_number" not in task_cols:
        op.add_column(
            "work_tasks",
            sa.Column(
                "sequence_number",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    # Refresh inspector after possible DDL.
    inspector = inspect(bind)
    task_cols = {c["name"] for c in inspector.get_columns("work_tasks")}
    if "reference" in task_cols and "sequence_number" in task_cols:
        types = bind.execute(
            sa.text("SELECT id, name FROM work_task_types")
        ).mappings().all()
        for task_type in types:
            tasks = bind.execute(
                sa.text(
                    "SELECT id FROM work_tasks WHERE task_type_id = :tid "
                    "ORDER BY created_at ASC, id ASC"
                ),
                {"tid": task_type["id"]},
            ).mappings().all()
            for index, task in enumerate(tasks, start=1):
                reference = f"{task_type['name']}-{index}"
                bind.execute(
                    sa.text(
                        "UPDATE work_tasks SET sequence_number = :n, reference = :ref "
                        "WHERE id = :id"
                    ),
                    {"n": index, "ref": reference, "id": task["id"]},
                )
            next_value = len(tasks) + 1
            bind.execute(
                sa.text(
                    "INSERT INTO work_task_type_sequences (task_type_id, next_value) "
                    "VALUES (:tid, :next) "
                    "ON CONFLICT (task_type_id) DO UPDATE "
                    "SET next_value = EXCLUDED.next_value"
                ),
                {"tid": task_type["id"], "next": next_value},
            )

    indexes = {idx["name"] for idx in inspector.get_indexes("work_tasks")}
    if "ix_work_tasks_reference" not in indexes:
        op.create_index(
            "ix_work_tasks_reference", "work_tasks", ["reference"], unique=False
        )

    uniques = {
        uq.get("name") for uq in inspector.get_unique_constraints("work_tasks")
    }
    # SQLAlchemy may also expose the composite unique via get_unique_constraints.
    if "uq_work_tasks_type_sequence" not in uniques:
        # Also check constraint names from table constraints for create_all leftovers.
        existing = bind.execute(
            sa.text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'work_tasks'::regclass AND contype = 'u'"
            )
        ).scalars().all()
        if "uq_work_tasks_type_sequence" not in existing:
            # Drop anonymous unique from SQLAlchemy create_all if present on same cols.
            for name in existing:
                cols = bind.execute(
                    sa.text(
                        "SELECT a.attname FROM pg_constraint c "
                        "JOIN pg_attribute a ON a.attrelid = c.conrelid "
                        "AND a.attnum = ANY (c.conkey) "
                        "WHERE c.conname = :name ORDER BY a.attnum"
                    ),
                    {"name": name},
                ).scalars().all()
                if list(cols) == ["task_type_id", "sequence_number"]:
                    op.drop_constraint(name, "work_tasks", type_="unique")
            op.create_unique_constraint(
                "uq_work_tasks_type_sequence",
                "work_tasks",
                ["task_type_id", "sequence_number"],
            )

    op.alter_column("work_tasks", "reference", server_default=None)
    op.alter_column("work_tasks", "sequence_number", server_default=None)
    if "work_task_type_sequences" in set(inspect(bind).get_table_names()):
        op.alter_column(
            "work_task_type_sequences", "next_value", server_default=None
        )


def downgrade() -> None:
    op.drop_constraint("uq_work_tasks_type_sequence", "work_tasks", type_="unique")
    op.drop_index("ix_work_tasks_reference", table_name="work_tasks")
    op.drop_column("work_tasks", "sequence_number")
    op.drop_column("work_tasks", "reference")
    op.drop_table("work_task_type_sequences")
