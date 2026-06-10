from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    timezone: Mapped[str] = mapped_column(String, nullable=False, default="America/Chicago")
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    accounts: Mapped[list["Account"]] = relationship(back_populates="user")


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    plaid_institution_id: Mapped[str | None] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class PlaidItem(Base):
    __tablename__ = "plaid_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    institution_id: Mapped[str | None] = mapped_column(ForeignKey("institutions.id", ondelete="SET NULL"))
    plaid_item_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    transactions_cursor: Mapped[str | None] = mapped_column(Text)
    products_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    available_products_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    consent_expires_at: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    last_successful_sync_at: Mapped[str | None] = mapped_column(String)
    last_failed_sync_at: Mapped[str | None] = mapped_column(String)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (Index("idx_accounts_user_classification", "user_id", "classification"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plaid_item_id: Mapped[str | None] = mapped_column(ForeignKey("plaid_items.id", ondelete="SET NULL"))
    plaid_account_id: Mapped[str | None] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    official_name: Mapped[str | None] = mapped_column(String)
    mask: Mapped[str | None] = mapped_column(String)
    type: Mapped[str] = mapped_column(String, nullable=False)
    subtype: Mapped[str | None] = mapped_column(String)
    classification: Mapped[str] = mapped_column(String, nullable=False)
    iso_currency_code: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    current_balance_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_balance_cents: Mapped[int | None] = mapped_column(Integer)
    credit_limit_cents: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_manual: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_balance_at: Mapped[str | None] = mapped_column(String)
    raw_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    user: Mapped[User] = relationship(back_populates="accounts")


class AccountBalanceSnapshot(Base):
    __tablename__ = "account_balance_snapshots"
    __table_args__ = (UniqueConstraint("account_id", "as_of_date", "source"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    as_of_date: Mapped[str] = mapped_column(String, nullable=False)
    current_balance_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    available_balance_cents: Mapped[int | None] = mapped_column(Integer)
    credit_limit_cents: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class BudgetCategory(Base):
    __tablename__ = "budget_categories"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("budget_categories.id", ondelete="SET NULL"))
    plaid_primary: Mapped[str | None] = mapped_column(String)
    plaid_detailed: Mapped[str | None] = mapped_column(String)
    color: Mapped[str | None] = mapped_column(String)
    is_income: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_archived: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("idx_transactions_user_date", "user_id", "posted_date"),
        Index("idx_transactions_account_date", "account_id", "posted_date"),
        Index("idx_transactions_category_date", "budget_category_id", "posted_date"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    plaid_transaction_id: Mapped[str | None] = mapped_column(String, unique=True)
    budget_category_id: Mapped[str | None] = mapped_column(ForeignKey("budget_categories.id", ondelete="SET NULL"))
    posted_date: Mapped[str] = mapped_column(String, nullable=False)
    authorized_date: Mapped[str | None] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(String)
    plaid_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    cash_flow_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    pending: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payment_channel: Mapped[str | None] = mapped_column(String)
    plaid_primary_category: Mapped[str | None] = mapped_column(String)
    plaid_detailed_category: Mapped[str | None] = mapped_column(String)
    iso_currency_code: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    is_removed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class RecurringStream(Base):
    __tablename__ = "recurring_streams"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    plaid_stream_id: Mapped[str | None] = mapped_column(String, unique=True)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, nullable=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("budget_categories.id", ondelete="SET NULL"))
    frequency: Mapped[str | None] = mapped_column(String)
    average_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    last_amount_cents: Mapped[int | None] = mapped_column(Integer)
    first_date: Mapped[str | None] = mapped_column(String)
    last_date: Mapped[str | None] = mapped_column(String)
    next_expected_date: Mapped[str | None] = mapped_column(String)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    raw_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class NetWorthSnapshot(Base):
    __tablename__ = "net_worth_snapshots"
    __table_args__ = (UniqueConstraint("user_id", "as_of_date"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    as_of_date: Mapped[str] = mapped_column(String, nullable=False)
    assets_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    debts_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    net_worth_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    cash_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    investments_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retirement_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    loans_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credit_cards_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class PlannedExpense(Base):
    __tablename__ = "planned_expenses"
    __table_args__ = (Index("idx_planned_expenses_user_date", "user_id", "due_date"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    due_date: Mapped[str] = mapped_column(String, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class FinancialGoal(Base):
    __tablename__ = "financial_goals"
    __table_args__ = (Index("idx_financial_goals_user_status", "user_id", "status"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    target_date: Mapped[str | None] = mapped_column(String)
    target_amount_cents: Mapped[int | None] = mapped_column(Integer)
    priority: Mapped[str] = mapped_column(String, nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    started_at: Mapped[str] = mapped_column(String, nullable=False)
    finished_at: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False)
    trigger: Mapped[str] = mapped_column(String, nullable=False)
    accounts_synced: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transactions_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transactions_modified: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transactions_removed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class AiSummary(Base):
    __tablename__ = "ai_summaries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    summary_type: Mapped[str] = mapped_column(String, nullable=False)
    period_start: Mapped[str] = mapped_column(String, nullable=False)
    period_end: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    insights_json: Mapped[str] = mapped_column(Text, nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
