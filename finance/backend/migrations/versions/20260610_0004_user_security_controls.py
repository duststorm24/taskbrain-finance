"""user security controls

Revision ID: 20260610_0004
Revises: 20260610_0003
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260610_0004"
down_revision = "20260610_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(), nullable=False, server_default="member"))
    op.add_column("users", sa.Column("status", sa.String(), nullable=False, server_default="active"))
    op.add_column("users", sa.Column("mfa_enabled", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("mfa_totp_secret_encrypted", sa.Text()))
    op.add_column("users", sa.Column("mfa_enabled_at", sa.String()))
    op.add_column("users", sa.Column("last_login_at", sa.String()))
    op.add_column("users", sa.Column("deactivated_at", sa.String()))
    op.execute("UPDATE users SET role = 'owner' WHERE id IN (SELECT id FROM users ORDER BY created_at ASC LIMIT 1)")
    op.create_index("idx_users_role_status", "users", ["role", "status"])


def downgrade() -> None:
    op.drop_index("idx_users_role_status", table_name="users")
    op.drop_column("users", "deactivated_at")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "mfa_enabled_at")
    op.drop_column("users", "mfa_totp_secret_encrypted")
    op.drop_column("users", "mfa_enabled")
    op.drop_column("users", "status")
    op.drop_column("users", "role")
