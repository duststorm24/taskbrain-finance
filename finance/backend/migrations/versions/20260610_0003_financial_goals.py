"""financial goals

Revision ID: 20260610_0003
Revises: 20260609_0002
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260610_0003"
down_revision = "20260609_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "financial_goals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("target_date", sa.String()),
        sa.Column("target_amount_cents", sa.Integer()),
        sa.Column("priority", sa.String(), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_index("idx_financial_goals_user_status", "financial_goals", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("idx_financial_goals_user_status", table_name="financial_goals")
    op.drop_table("financial_goals")
