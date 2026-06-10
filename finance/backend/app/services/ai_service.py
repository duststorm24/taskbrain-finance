from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import new_id, utcnow
from app.db.models import Account, AiSummary, FinancialGoal, NetWorthSnapshot, PlannedExpense, RecurringStream, Transaction, User


AnalysisMode = Literal["daily", "detailed", "complete"]

MODE_CONFIG: dict[AnalysisMode, dict[str, int]] = {
    "daily": {"lookback_days": 45, "recent_transactions": 25, "trend_points": 20, "max_output_tokens": 1200},
    "detailed": {"lookback_days": 365, "recent_transactions": 100, "trend_points": 80, "max_output_tokens": 3000},
    "complete": {"lookback_days": 3650, "recent_transactions": 250, "trend_points": 240, "max_output_tokens": 6000},
}


def list_ai_summaries(db: Session, user_id: str, limit: int = 12) -> list[AiSummary]:
    return (
        db.query(AiSummary)
        .filter(AiSummary.user_id == user_id)
        .order_by(AiSummary.created_at.desc())
        .limit(limit)
        .all()
    )


def generate_analysis(db: Session, user: User, mode: AnalysisMode) -> AiSummary:
    settings = get_settings()
    model = settings.openai_model_for_mode(mode)
    context = _build_financial_context(db, user, mode, model)
    fingerprint = _fingerprint(context)
    prompt = _analysis_prompt(mode, context)

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You are TaskBrain Finance's local financial analysis engine. "
                            "Use the provided data to produce practical budgeting, debt, cash-flow, and planning analysis. "
                            "Do not ask for secrets, account numbers, login credentials, or Plaid/OpenAI tokens. "
                            "Be clear when data is incomplete. This is educational planning support, not tax, legal, or investment advisory."
                        ),
                    }
                ],
            },
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
        ],
        max_output_tokens=int(MODE_CONFIG[mode]["max_output_tokens"]),
    )
    markdown = getattr(response, "output_text", "").strip()
    if not markdown:
        markdown = "Analysis completed, but the model returned no readable text."

    now = utcnow()
    period_start = str(context["period"]["start_date"])
    period_end = str(context["period"]["end_date"])
    summary = AiSummary(
        id=new_id(),
        user_id=user.id,
        summary_type=mode,
        period_start=period_start,
        period_end=period_end,
        model=model,
        title=_title_for_mode(mode),
        summary_markdown=markdown,
        insights_json=json.dumps(
            {
                "mode": mode,
                "model": model,
                "context": context["metadata"],
                "baseline_summary_id": (context.get("baseline_summary") or {}).get("id"),
                "token_and_secret_policy": "No Plaid access tokens, API keys, account masks, or raw integration secrets are included.",
            },
            separators=(",", ":"),
        ),
        input_fingerprint=fingerprint,
        created_at=now,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary


def _build_financial_context(db: Session, user: User, mode: AnalysisMode, model: str) -> dict[str, Any]:
    today = datetime.now(UTC).date()
    lookback_days = MODE_CONFIG[mode]["lookback_days"]
    start_date = today - timedelta(days=lookback_days)

    accounts = db.query(Account).filter(Account.user_id == user.id, Account.is_active == 1).order_by(Account.name).all()
    snapshots = (
        db.query(NetWorthSnapshot)
        .filter(NetWorthSnapshot.user_id == user.id)
        .order_by(NetWorthSnapshot.as_of_date.desc())
        .limit(MODE_CONFIG[mode]["trend_points"])
        .all()
    )
    snapshots = list(reversed(snapshots))
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id, Transaction.is_removed == 0, Transaction.posted_date >= start_date.isoformat())
        .order_by(Transaction.posted_date.desc(), Transaction.updated_at.desc())
        .all()
    )
    recurring = (
        db.query(RecurringStream)
        .filter(RecurringStream.user_id == user.id, RecurringStream.is_active == 1)
        .order_by(RecurringStream.next_expected_date.asc())
        .all()
    )
    planned_expenses = (
        db.query(PlannedExpense)
        .filter(PlannedExpense.user_id == user.id, PlannedExpense.due_date >= today.isoformat())
        .order_by(PlannedExpense.due_date.asc(), PlannedExpense.amount_cents.desc())
        .limit(80)
        .all()
    )
    goals = (
        db.query(FinancialGoal)
        .filter(FinancialGoal.user_id == user.id, FinancialGoal.status == "active")
        .order_by(FinancialGoal.target_date.asc(), FinancialGoal.created_at.asc())
        .limit(80)
        .all()
    )
    baseline = _latest_complete_baseline(db, user.id) if mode != "complete" else None

    period_start = _earliest_period_date(transactions, snapshots, start_date, mode)
    monthly_cash_flow = _monthly_cash_flow(transactions, period_start, today)
    category_spending = _category_spending(transactions)
    recent_transactions = transactions[: MODE_CONFIG[mode]["recent_transactions"]]

    account_rows = [_account_context(account) for account in accounts]
    return {
        "metadata": {
            "mode": mode,
            "model": model,
            "generated_at": utcnow(),
            "account_count": len(account_rows),
            "transaction_count_in_packet": len(recent_transactions),
            "transaction_count_analyzed": len(transactions),
            "planned_expense_count": len(planned_expenses),
            "financial_goal_count": len(goals),
            "recurring_stream_count": len(recurring),
        },
        "user": {
            "display_name": user.display_name,
            "timezone": user.timezone,
        },
        "period": {
            "start_date": period_start.isoformat(),
            "end_date": today.isoformat(),
        },
        "balances": {
            "assets_cents": sum(_asset_value(account) for account in accounts),
            "debts_cents": sum(_debt_value(account) for account in accounts),
            "net_worth_cents": sum(_asset_value(account) for account in accounts) - sum(_debt_value(account) for account in accounts),
            "cash_cents": sum(_asset_value(account) for account in accounts if account.type == "depository"),
            "investments_cents": sum(_asset_value(account) for account in accounts if account.type == "investment"),
            "credit_cards_cents": sum(_debt_value(account) for account in accounts if account.type == "credit"),
            "loans_cents": sum(_debt_value(account) for account in accounts if account.type == "loan"),
        },
        "accounts": account_rows,
        "net_worth_trend": [
            {
                "date": row.as_of_date,
                "assets_cents": row.assets_cents,
                "debts_cents": row.debts_cents,
                "net_worth_cents": row.net_worth_cents,
                "cash_cents": row.cash_cents,
                "investments_cents": row.investments_cents,
                "retirement_cents": row.retirement_cents,
            }
            for row in snapshots
        ],
        "monthly_cash_flow": monthly_cash_flow,
        "category_spending": category_spending[:20],
        "recurring_streams": [
            {
                "direction": stream.direction,
                "merchant_name": stream.merchant_name,
                "description": stream.description,
                "frequency": stream.frequency,
                "average_amount_cents": stream.average_amount_cents,
                "last_amount_cents": stream.last_amount_cents,
                "next_expected_date": stream.next_expected_date,
            }
            for stream in recurring[:40]
        ],
        "planned_expenses": [
            {
                "title": expense.title,
                "due_date": expense.due_date,
                "amount_cents": expense.amount_cents,
                "category": expense.category,
                "notes": expense.notes,
            }
            for expense in planned_expenses
        ],
        "financial_goals": [
            {
                "title": goal.title,
                "target_date": goal.target_date,
                "target_amount_cents": goal.target_amount_cents,
                "priority": goal.priority,
                "notes": goal.notes,
            }
            for goal in goals
        ],
        "recent_transactions": [
            {
                "posted_date": transaction.posted_date,
                "description": transaction.merchant_name or transaction.description,
                "cash_flow_cents": transaction.cash_flow_cents,
                "category": transaction.plaid_primary_category or transaction.plaid_detailed_category or "Uncategorized",
                "pending": bool(transaction.pending),
            }
            for transaction in recent_transactions
        ],
        "baseline_summary": _baseline_context(baseline),
    }


def _analysis_prompt(mode: AnalysisMode, context: dict[str, Any]) -> str:
    if mode == "daily":
        mode_instruction = (
            "Create a compact daily review. Include: current readout, notable changes or anomalies, "
            "upcoming planned expenses and recovery impact, budget/cash-flow suggestions, and 3 prioritized next actions."
        )
    elif mode == "detailed":
        mode_instruction = (
            "Create a detailed financial analysis. Include: cash-flow trend, category anomalies, recurring expenses, "
            "planned one-time expense readiness, goal progress, debt payoff recommendations, investment contribution notes, "
            "forecast risks, and a short action plan."
        )
    else:
        mode_instruction = (
            "Create a complete baseline financial deep analysis. This should be suitable as a yearly or initial benchmark. "
            "Include: baseline financial map, account mix, cash-flow engine, recurring obligations, upcoming known expenses, "
            "goal feasibility, debt strategy, investment trajectory considerations, risk watchlist, assumptions, and what future daily "
            "or detailed reviews should compare against."
        )

    return (
        f"{mode_instruction}\n\n"
        "Write in clear markdown with short sections and specific dollar amounts when useful. "
        "Do not mention internal ids, database implementation, Plaid tokens, or API keys. "
        "If the data is mostly empty, say what needs to be synced or entered next.\n\n"
        "Financial context JSON:\n"
        f"{json.dumps(context, indent=2, sort_keys=True)}"
    )


def _account_context(account: Account) -> dict[str, Any]:
    return {
        "name": account.name,
        "type": account.type,
        "subtype": account.subtype,
        "classification": account.classification,
        "current_balance_cents": account.current_balance_cents,
        "available_balance_cents": account.available_balance_cents,
        "credit_limit_cents": account.credit_limit_cents,
        "last_balance_at": account.last_balance_at,
    }


def _monthly_cash_flow(transactions: list[Transaction], start_date: date, end_date: date) -> list[dict[str, int | str]]:
    months: dict[str, dict[str, int | str]] = {}
    cursor = start_date.replace(day=1)
    final = end_date.replace(day=1)
    while cursor <= final:
        key = f"{cursor.year}-{cursor.month:02d}"
        months[key] = {"month": key, "income_cents": 0, "expense_cents": 0, "net_cents": 0, "transaction_count": 0}
        cursor = _add_months(cursor, 1)

    for transaction in transactions:
        month = transaction.posted_date[:7]
        if month not in months:
            continue
        months[month]["net_cents"] = int(months[month]["net_cents"]) + transaction.cash_flow_cents
        months[month]["transaction_count"] = int(months[month]["transaction_count"]) + 1
        if transaction.cash_flow_cents >= 0:
            months[month]["income_cents"] = int(months[month]["income_cents"]) + transaction.cash_flow_cents
        else:
            months[month]["expense_cents"] = int(months[month]["expense_cents"]) + abs(transaction.cash_flow_cents)
    return list(months.values())[-36:]


def _category_spending(transactions: list[Transaction]) -> list[dict[str, int | str]]:
    categories: dict[str, dict[str, int | str]] = {}
    for transaction in transactions:
        if transaction.cash_flow_cents >= 0:
            continue
        name = transaction.plaid_primary_category or transaction.plaid_detailed_category or "Uncategorized"
        row = categories.setdefault(name, {"category": name, "spent_cents": 0, "transaction_count": 0})
        row["spent_cents"] = int(row["spent_cents"]) + abs(transaction.cash_flow_cents)
        row["transaction_count"] = int(row["transaction_count"]) + 1
    return sorted(categories.values(), key=lambda item: int(item["spent_cents"]), reverse=True)


def _latest_complete_baseline(db: Session, user_id: str) -> AiSummary | None:
    return (
        db.query(AiSummary)
        .filter(AiSummary.user_id == user_id, AiSummary.summary_type == "complete")
        .order_by(AiSummary.created_at.desc())
        .first()
    )


def _baseline_context(summary: AiSummary | None) -> dict[str, str] | None:
    if summary is None:
        return None
    return {
        "id": summary.id,
        "created_at": summary.created_at,
        "title": summary.title,
        "summary_markdown_excerpt": summary.summary_markdown[:5000],
    }


def _earliest_period_date(transactions: list[Transaction], snapshots: list[NetWorthSnapshot], fallback: date, mode: AnalysisMode) -> date:
    if mode != "complete":
        return fallback
    candidates: list[date] = []
    if transactions:
        candidates.append(_parse_date(transactions[-1].posted_date))
    if snapshots:
        candidates.append(_parse_date(snapshots[0].as_of_date))
    return min(candidates) if candidates else fallback


def _parse_date(value: str) -> date:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _asset_value(account: Account) -> int:
    return abs(account.current_balance_cents) if account.classification == "asset" else 0


def _debt_value(account: Account) -> int:
    return abs(account.current_balance_cents) if account.classification == "debt" else 0


def _fingerprint(context: dict[str, Any]) -> str:
    payload = json.dumps(context, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _title_for_mode(mode: AnalysisMode) -> str:
    if mode == "daily":
        return "Daily Financial Review"
    if mode == "detailed":
        return "Detailed Financial Analysis"
    return "Complete Financial Deep Analysis"
