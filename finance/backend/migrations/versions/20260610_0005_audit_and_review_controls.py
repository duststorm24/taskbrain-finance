"""audit and review controls

Revision ID: 20260610_0005
Revises: 20260610_0004
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260610_0005"
down_revision = "20260610_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("actor_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("target_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False, server_default="success"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index("idx_audit_events_created", "audit_events", ["created_at"])
    op.create_index("idx_audit_events_actor", "audit_events", ["actor_user_id", "created_at"])

    op.create_table(
        "access_reviews",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("period_start", sa.String(), nullable=False),
        sa.Column("period_end", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("completed_at", sa.String()),
    )
    op.create_index("idx_access_reviews_status", "access_reviews", ["status", "created_at"])

    op.create_table(
        "access_review_users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("review_id", sa.String(), sa.ForeignKey("access_reviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("mfa_enabled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_login_at", sa.String()),
        sa.Column("decision", sa.String(), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.UniqueConstraint("review_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("access_review_users")
    op.drop_index("idx_access_reviews_status", table_name="access_reviews")
    op.drop_table("access_reviews")
    op.drop_index("idx_audit_events_actor", table_name="audit_events")
    op.drop_index("idx_audit_events_created", table_name="audit_events")
    op.drop_table("audit_events")
