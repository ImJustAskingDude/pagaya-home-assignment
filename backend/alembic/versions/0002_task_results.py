"""add task results

Revision ID: 0002_task_results
Revises: 0001_initial_schema
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_task_results"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("queue_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
    )
    op.execute(
        """
        INSERT INTO task_results (task_id, queue_id, type, status, result, error, created_at)
        SELECT id, queue_id, type, status, result, error, COALESCE(finished_at, created_at)
        FROM tasks
        WHERE status IN ('succeeded', 'failed', 'cancelled')
        """
    )
    op.create_index("ix_task_results_task_id", "task_results", ["task_id"])
    op.create_index("ix_task_results_queue_id", "task_results", ["queue_id"])
    op.create_index("ix_task_results_type", "task_results", ["type"])
    op.create_index("ix_task_results_status", "task_results", ["status"])
    op.create_index("ix_task_results_created_at", "task_results", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_task_results_created_at", table_name="task_results")
    op.drop_index("ix_task_results_status", table_name="task_results")
    op.drop_index("ix_task_results_type", table_name="task_results")
    op.drop_index("ix_task_results_queue_id", table_name="task_results")
    op.drop_index("ix_task_results_task_id", table_name="task_results")
    op.drop_table("task_results")
