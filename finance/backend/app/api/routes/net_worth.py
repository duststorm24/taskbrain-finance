from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import Account, NetWorthSnapshot, User
from app.db.session import get_db


router = APIRouter()


@router.get("")
def net_worth(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    accounts = db.query(Account).filter(Account.user_id == user.id, Account.is_active == 1).order_by(Account.name).all()
    latest_snapshot = (
        db.query(NetWorthSnapshot)
        .filter(NetWorthSnapshot.user_id == user.id)
        .order_by(NetWorthSnapshot.as_of_date.desc())
        .first()
    )
    trend = (
        db.query(NetWorthSnapshot)
        .filter(NetWorthSnapshot.user_id == user.id)
        .order_by(NetWorthSnapshot.as_of_date)
        .all()
    )

    return {
        "user_id": user.id,
        "currentNetWorthCents": latest_snapshot.net_worth_cents if latest_snapshot else 0,
        "assetsCents": latest_snapshot.assets_cents if latest_snapshot else 0,
        "debtsCents": latest_snapshot.debts_cents if latest_snapshot else 0,
        "trend": [{"date": row.as_of_date, "netWorthCents": row.net_worth_cents} for row in trend],
        "assetAllocation": _allocation(accounts, "asset"),
        "debtAllocation": _allocation(accounts, "debt"),
        "accounts": [
            {
                "id": account.id,
                "name": account.name,
                "type": account.type,
                "subtype": account.subtype,
                "classification": account.classification,
                "currentBalanceCents": account.current_balance_cents,
                "availableBalanceCents": account.available_balance_cents,
                "lastBalanceAt": account.last_balance_at,
            }
            for account in accounts
        ],
    }


def _allocation(accounts: list[Account], classification: str) -> list[dict[str, object]]:
    totals: dict[str, int] = {}
    for account in accounts:
        if account.classification != classification:
            continue
        key = account.subtype or account.type
        totals[key] = totals.get(key, 0) + abs(account.current_balance_cents)
    return [{"name": name, "valueCents": value} for name, value in sorted(totals.items()) if value]
