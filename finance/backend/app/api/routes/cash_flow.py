from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import RecurringStream, Transaction, User
from app.db.session import get_db


router = APIRouter()


@router.get("")
def cash_flow(
    months: int = Query(default=12, ge=1, le=36),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    today = datetime.now(UTC).date()
    start_month = _add_months(today.replace(day=1), -(months - 1))
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user.id,
            Transaction.is_removed == 0,
            Transaction.pending == 0,
            Transaction.posted_date >= start_month.isoformat(),
        )
        .order_by(Transaction.posted_date.asc())
        .all()
    )

    monthly = {
        _month_key(_add_months(start_month, offset)): {
            "month": _month_key(_add_months(start_month, offset)),
            "incomeCents": 0,
            "expenseCents": 0,
            "netCents": 0,
            "transactionCount": 0,
        }
        for offset in range(months)
    }
    categories: dict[str, dict[str, object]] = {}

    for transaction in transactions:
        month = transaction.posted_date[:7]
        if month not in monthly:
            continue
        cash_flow_cents = transaction.cash_flow_cents
        monthly[month]["netCents"] += cash_flow_cents
        monthly[month]["transactionCount"] += 1
        if cash_flow_cents >= 0:
            monthly[month]["incomeCents"] += cash_flow_cents
        else:
            expense_cents = abs(cash_flow_cents)
            monthly[month]["expenseCents"] += expense_cents
            category_name = transaction.plaid_primary_category or transaction.plaid_detailed_category or "Uncategorized"
            category = categories.setdefault(
                category_name,
                {"category": category_name, "spentCents": 0, "transactionCount": 0},
            )
            category["spentCents"] += expense_cents
            category["transactionCount"] += 1

    category_rows = sorted(categories.values(), key=lambda row: int(row["spentCents"]), reverse=True)
    recent_transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id, Transaction.is_removed == 0)
        .order_by(Transaction.posted_date.desc(), Transaction.updated_at.desc())
        .limit(12)
        .all()
    )

    return {
        "user_id": user.id,
        "incomeCents": sum(int(row["incomeCents"]) for row in monthly.values()),
        "expenseCents": sum(int(row["expenseCents"]) for row in monthly.values()),
        "netCents": sum(int(row["netCents"]) for row in monthly.values()),
        "monthlyCashFlow": list(monthly.values()),
        "categories": category_rows[:10],
        "recentTransactions": [
            {
                "id": transaction.id,
                "postedDate": transaction.posted_date,
                "description": transaction.merchant_name or transaction.description,
                "cashFlowCents": transaction.cash_flow_cents,
                "category": transaction.plaid_primary_category or transaction.plaid_detailed_category or "Uncategorized",
                "pending": bool(transaction.pending),
            }
            for transaction in recent_transactions
        ],
    }


@router.get("/recurring")
def recurring_expenses(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    streams = (
        db.query(RecurringStream)
        .filter(RecurringStream.user_id == user.id, RecurringStream.is_active == 1)
        .order_by(RecurringStream.direction.desc(), RecurringStream.next_expected_date.asc())
        .all()
    )
    return {
        "user_id": user.id,
        "streams": [
            {
                "id": stream.id,
                "direction": stream.direction,
                "merchantName": stream.merchant_name,
                "description": stream.description,
                "frequency": stream.frequency,
                "averageAmountCents": stream.average_amount_cents,
                "lastAmountCents": stream.last_amount_cents,
                "firstDate": stream.first_date,
                "lastDate": stream.last_date,
                "nextExpectedDate": stream.next_expected_date,
            }
            for stream in streams
        ],
    }


def _month_key(value: date) -> str:
    return f"{value.year}-{value.month:02d}"


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)
