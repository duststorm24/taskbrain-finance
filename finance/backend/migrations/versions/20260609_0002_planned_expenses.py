"""planned expenses

Revision ID: 20260609_0002
Revises: 20260609_0001
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa


revision = "20260609_0002"
down_revision = "20260609_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "planned_expenses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("due_date", sa.String(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("category", sa.String()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_index("idx_planned_expenses_user_date", "planned_expenses", ["user_id", "due_date"])


def downgrade() -> None:
    op.drop_index("idx_planned_expenses_user_date", table_name="planned_expenses")
    op.drop_table("planned_expenses")

