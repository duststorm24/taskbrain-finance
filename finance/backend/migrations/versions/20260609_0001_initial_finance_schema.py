"""initial finance schema

Revision ID: 20260609_0001
Revises:
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa


revision = "20260609_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_table(
        "institutions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("plaid_institution_id", sa.String(), unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_table(
        "plaid_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution_id", sa.String(), sa.ForeignKey("institutions.id", ondelete="SET NULL")),
        sa.Column("plaid_item_id", sa.String(), nullable=False, unique=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("transactions_cursor", sa.Text()),
        sa.Column("products_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("available_products_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("consent_expires_at", sa.String()),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("last_successful_sync_at", sa.String()),
        sa.Column("last_failed_sync_at", sa.String()),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plaid_item_id", sa.String(), sa.ForeignKey("plaid_items.id", ondelete="SET NULL")),
        sa.Column("plaid_account_id", sa.String(), unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("official_name", sa.String()),
        sa.Column("mask", sa.String()),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("subtype", sa.String()),
        sa.Column("classification", sa.String(), nullable=False),
        sa.Column("iso_currency_code", sa.String(), nullable=False, server_default="USD"),
        sa.Column("current_balance_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_balance_cents", sa.Integer()),
        sa.Column("credit_limit_cents", sa.Integer()),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_manual", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_balance_at", sa.String()),
        sa.Column("raw_json", sa.Text()),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_index("idx_accounts_user_classification", "accounts", ["user_id", "classification"])
    op.create_table(
        "account_balance_snapshots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("as_of_date", sa.String(), nullable=False),
        sa.Column("current_balance_cents", sa.Integer(), nullable=False),
        sa.Column("available_balance_cents", sa.Integer()),
        sa.Column("credit_limit_cents", sa.Integer()),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.UniqueConstraint("account_id", "as_of_date", "source"),
    )
    op.create_table(
        "budget_categories",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("parent_id", sa.String(), sa.ForeignKey("budget_categories.id", ondelete="SET NULL")),
        sa.Column("plaid_primary", sa.String()),
        sa.Column("plaid_detailed", sa.String()),
        sa.Column("color", sa.String()),
        sa.Column("is_income", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_archived", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.UniqueConstraint("user_id", "name"),
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plaid_transaction_id", sa.String(), unique=True),
        sa.Column("budget_category_id", sa.String(), sa.ForeignKey("budget_categories.id", ondelete="SET NULL")),
        sa.Column("posted_date", sa.String(), nullable=False),
        sa.Column("authorized_date", sa.String()),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("merchant_name", sa.String()),
        sa.Column("plaid_amount_cents", sa.Integer(), nullable=False),
        sa.Column("cash_flow_cents", sa.Integer(), nullable=False),
        sa.Column("pending", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payment_channel", sa.String()),
        sa.Column("plaid_primary_category", sa.String()),
        sa.Column("plaid_detailed_category", sa.String()),
        sa.Column("iso_currency_code", sa.String(), nullable=False, server_default="USD"),
        sa.Column("is_removed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_json", sa.Text()),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_index("idx_transactions_user_date", "transactions", ["user_id", "posted_date"])
    op.create_index("idx_transactions_account_date", "transactions", ["account_id", "posted_date"])
    op.create_index("idx_transactions_category_date", "transactions", ["budget_category_id", "posted_date"])
    op.create_table(
        "recurring_streams",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id", ondelete="SET NULL")),
        sa.Column("plaid_stream_id", sa.String(), unique=True),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("merchant_name", sa.String()),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("category_id", sa.String(), sa.ForeignKey("budget_categories.id", ondelete="SET NULL")),
        sa.Column("frequency", sa.String()),
        sa.Column("average_amount_cents", sa.Integer(), nullable=False),
        sa.Column("last_amount_cents", sa.Integer()),
        sa.Column("first_date", sa.String()),
        sa.Column("last_date", sa.String()),
        sa.Column("next_expected_date", sa.String()),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("raw_json", sa.Text()),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_table(
        "net_worth_snapshots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("as_of_date", sa.String(), nullable=False),
        sa.Column("assets_cents", sa.Integer(), nullable=False),
        sa.Column("debts_cents", sa.Integer(), nullable=False),
        sa.Column("net_worth_cents", sa.Integer(), nullable=False),
        sa.Column("cash_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("investments_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retirement_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("loans_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("credit_cards_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.UniqueConstraint("user_id", "as_of_date"),
    )
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("started_at", sa.String(), nullable=False),
        sa.Column("finished_at", sa.String()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("trigger", sa.String(), nullable=False),
        sa.Column("accounts_synced", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transactions_added", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transactions_modified", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transactions_removed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_table(
        "ai_summaries",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary_type", sa.String(), nullable=False),
        sa.Column("period_start", sa.String(), nullable=False),
        sa.Column("period_end", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary_markdown", sa.Text(), nullable=False),
        sa.Column("insights_json", sa.Text(), nullable=False),
        sa.Column("input_fingerprint", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ai_summaries")
    op.drop_table("sync_runs")
    op.drop_table("net_worth_snapshots")
    op.drop_table("recurring_streams")
    op.drop_index("idx_transactions_category_date", table_name="transactions")
    op.drop_index("idx_transactions_account_date", table_name="transactions")
    op.drop_index("idx_transactions_user_date", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("budget_categories")
    op.drop_table("account_balance_snapshots")
    op.drop_index("idx_accounts_user_classification", table_name="accounts")
    op.drop_table("accounts")
    op.drop_table("plaid_items")
    op.drop_table("institutions")
    op.drop_table("users")

