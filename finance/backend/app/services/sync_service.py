import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.core.encryption import decrypt_secret
from app.core.security import new_id, utcnow
from app.db.models import Account, AccountBalanceSnapshot, NetWorthSnapshot, PlaidItem, RecurringStream, SyncRun, Transaction
from app.services.plaid_service import get_accounts, get_recurring_transactions, get_transaction_updates


def sync_user_finances(db: Session, user_id: str, trigger: str = "manual") -> SyncRun:
    now = utcnow()
    sync_run = SyncRun(
        id=new_id(),
        user_id=user_id,
        started_at=now,
        status="running",
        trigger=trigger,
        metadata_json="{}",
    )
    db.add(sync_run)
    db.flush()

    try:
        active_items = db.query(PlaidItem).filter(PlaidItem.user_id == user_id, PlaidItem.status == "active").all()
        accounts_synced = 0
        transactions_added = 0
        transactions_modified = 0
        transactions_removed = 0
        recurring_streams_synced = 0
        recurring_errors: list[str] = []
        transaction_statuses: list[str] = []

        for item in active_items:
            access_token = decrypt_secret(item.access_token_encrypted)
            payload = get_accounts(access_token)
            accounts_synced += _sync_accounts_for_item(db, user_id, item, payload.get("accounts", []))

            transaction_updates = get_transaction_updates(access_token, item.transactions_cursor)
            added_count, modified_count, removed_count = _sync_transactions_for_item(
                db,
                user_id,
                transaction_updates.get("added", []),
                transaction_updates.get("modified", []),
                transaction_updates.get("removed", []),
            )
            transactions_added += added_count
            transactions_modified += modified_count
            transactions_removed += removed_count
            if transaction_updates.get("next_cursor"):
                item.transactions_cursor = transaction_updates["next_cursor"]
            if transaction_updates.get("transactions_update_status"):
                transaction_statuses.append(str(transaction_updates["transactions_update_status"]))

            try:
                recurring_payload = get_recurring_transactions(access_token)
                recurring_streams_synced += _sync_recurring_streams(db, user_id, recurring_payload)
            except Exception as exc:
                recurring_errors.append(str(exc))

            item.last_successful_sync_at = utcnow()
            item.last_error = None
            item.updated_at = utcnow()

        net_worth = _create_net_worth_snapshot(db, user_id)
        sync_run.finished_at = utcnow()
        sync_run.status = "success"
        sync_run.accounts_synced = accounts_synced
        sync_run.transactions_added = transactions_added
        sync_run.transactions_modified = transactions_modified
        sync_run.transactions_removed = transactions_removed
        sync_run.metadata_json = json.dumps(
            {
                "net_worth_cents": net_worth.net_worth_cents,
                "recurring_streams_synced": recurring_streams_synced,
                "recurring_errors": recurring_errors,
                "transactions_update_statuses": transaction_statuses,
            }
        )
        db.flush()
        return sync_run
    except Exception as exc:
        sync_run.finished_at = utcnow()
        sync_run.status = "failed"
        sync_run.error = str(exc)
        db.flush()
        raise


def _sync_accounts_for_item(db: Session, user_id: str, item: PlaidItem, accounts: list[dict]) -> int:
    synced = 0
    now = utcnow()
    as_of_date = datetime.now(UTC).date().isoformat()

    for account_payload in accounts:
        plaid_account_id = account_payload["account_id"]
        balances = account_payload.get("balances") or {}
        account = db.query(Account).filter(Account.plaid_account_id == plaid_account_id).one_or_none()

        if account is None:
            account = Account(
                id=new_id(),
                user_id=user_id,
                plaid_item_id=item.id,
                plaid_account_id=plaid_account_id,
                name=account_payload.get("name") or "Unnamed account",
                type=str(account_payload.get("type") or "unknown"),
                classification=_classify_account(account_payload.get("type"), account_payload.get("subtype")),
                created_at=now,
                updated_at=now,
            )
            db.add(account)

        account.plaid_item_id = item.id
        account.name = account_payload.get("name") or account.name
        account.official_name = account_payload.get("official_name")
        account.mask = account_payload.get("mask")
        account.type = str(account_payload.get("type") or account.type)
        account.subtype = account_payload.get("subtype")
        account.classification = _classify_account(account.type, account.subtype)
        account.iso_currency_code = balances.get("iso_currency_code") or account.iso_currency_code or "USD"
        account.current_balance_cents = _money_to_cents(balances.get("current"))
        account.available_balance_cents = _optional_money_to_cents(balances.get("available"))
        account.credit_limit_cents = _optional_money_to_cents(balances.get("limit"))
        account.is_active = 1
        account.last_balance_at = now
        account.raw_json = json.dumps(account_payload, separators=(",", ":"), default=str)
        account.updated_at = now
        db.flush()

        snapshot = (
            db.query(AccountBalanceSnapshot)
            .filter(
                AccountBalanceSnapshot.account_id == account.id,
                AccountBalanceSnapshot.as_of_date == as_of_date,
                AccountBalanceSnapshot.source == "plaid",
            )
            .one_or_none()
        )
        if snapshot is None:
            snapshot = AccountBalanceSnapshot(
                id=new_id(),
                account_id=account.id,
                as_of_date=as_of_date,
                source="plaid",
                created_at=now,
                current_balance_cents=account.current_balance_cents,
            )
            db.add(snapshot)

        snapshot.current_balance_cents = account.current_balance_cents
        snapshot.available_balance_cents = account.available_balance_cents
        snapshot.credit_limit_cents = account.credit_limit_cents
        synced += 1

    return synced


def _sync_transactions_for_item(
    db: Session,
    user_id: str,
    added: list[dict[str, Any]],
    modified: list[dict[str, Any]],
    removed: list[dict[str, Any]],
) -> tuple[int, int, int]:
    added_count = 0
    modified_count = 0
    removed_count = 0

    for transaction_payload in added:
        if _upsert_transaction(db, user_id, transaction_payload, is_new=True):
            added_count += 1

    for transaction_payload in modified:
        if _upsert_transaction(db, user_id, transaction_payload, is_new=False):
            modified_count += 1

    for removed_payload in removed:
        transaction_id = removed_payload.get("transaction_id")
        if not transaction_id:
            continue
        transaction = (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id, Transaction.plaid_transaction_id == transaction_id)
            .one_or_none()
        )
        if transaction is None:
            continue
        transaction.is_removed = 1
        transaction.updated_at = utcnow()
        removed_count += 1

    return added_count, modified_count, removed_count


def _upsert_transaction(db: Session, user_id: str, payload: dict[str, Any], *, is_new: bool) -> bool:
    plaid_transaction_id = payload.get("transaction_id")
    plaid_account_id = payload.get("account_id")
    if not plaid_transaction_id or not plaid_account_id:
        return False

    account = db.query(Account).filter(Account.user_id == user_id, Account.plaid_account_id == plaid_account_id).one_or_none()
    if account is None:
        return False

    now = utcnow()
    transaction = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.plaid_transaction_id == plaid_transaction_id)
        .one_or_none()
    )
    if transaction is None:
        transaction = Transaction(
            id=new_id(),
            user_id=user_id,
            account_id=account.id,
            plaid_transaction_id=plaid_transaction_id,
            posted_date=_date_to_string(payload.get("date")),
            description=str(payload.get("name") or payload.get("merchant_name") or "Unnamed transaction"),
            plaid_amount_cents=0,
            cash_flow_cents=0,
            created_at=now,
            updated_at=now,
        )
        db.add(transaction)
    elif is_new:
        return False

    personal_category = payload.get("personal_finance_category") or {}
    amount_cents = _money_to_cents(payload.get("amount"))

    transaction.account_id = account.id
    transaction.posted_date = _date_to_string(payload.get("date"))
    transaction.authorized_date = _optional_date_to_string(payload.get("authorized_date"))
    transaction.description = str(payload.get("name") or payload.get("merchant_name") or transaction.description)
    transaction.merchant_name = payload.get("merchant_name")
    transaction.plaid_amount_cents = amount_cents
    transaction.cash_flow_cents = -amount_cents
    transaction.pending = 1 if payload.get("pending") else 0
    transaction.payment_channel = payload.get("payment_channel")
    transaction.plaid_primary_category = personal_category.get("primary") or _legacy_category(payload, 0)
    transaction.plaid_detailed_category = personal_category.get("detailed") or _legacy_category(payload, 1)
    transaction.iso_currency_code = payload.get("iso_currency_code") or transaction.iso_currency_code or "USD"
    transaction.is_removed = 0
    transaction.raw_json = json.dumps(payload, separators=(",", ":"), default=str)
    transaction.updated_at = now
    return True


def _sync_recurring_streams(db: Session, user_id: str, payload: dict[str, Any]) -> int:
    count = 0
    active_stream_ids: set[str] = set()

    for direction, stream_key in (("inflow", "inflow_streams"), ("outflow", "outflow_streams")):
        for stream_payload in payload.get(stream_key, []):
            stream_id = stream_payload.get("stream_id")
            if not stream_id:
                continue
            active_stream_ids.add(stream_id)
            _upsert_recurring_stream(db, user_id, stream_payload, direction)
            count += 1

    if active_stream_ids:
        existing_streams = db.query(RecurringStream).filter(RecurringStream.user_id == user_id).all()
        for stream in existing_streams:
            if stream.plaid_stream_id not in active_stream_ids:
                stream.is_active = 0
                stream.updated_at = utcnow()

    return count


def _upsert_recurring_stream(db: Session, user_id: str, payload: dict[str, Any], direction: str) -> None:
    stream_id = payload["stream_id"]
    now = utcnow()
    account = None
    if payload.get("account_id"):
        account = db.query(Account).filter(Account.user_id == user_id, Account.plaid_account_id == payload["account_id"]).one_or_none()

    stream = (
        db.query(RecurringStream)
        .filter(RecurringStream.user_id == user_id, RecurringStream.plaid_stream_id == stream_id)
        .one_or_none()
    )
    if stream is None:
        stream = RecurringStream(
            id=new_id(),
            user_id=user_id,
            plaid_stream_id=stream_id,
            direction=direction,
            description=str(payload.get("description") or payload.get("merchant_name") or "Recurring transaction"),
            average_amount_cents=0,
            created_at=now,
            updated_at=now,
        )
        db.add(stream)

    stream.account_id = account.id if account else None
    stream.direction = direction
    stream.merchant_name = payload.get("merchant_name")
    stream.description = str(payload.get("description") or payload.get("merchant_name") or stream.description)
    stream.frequency = payload.get("frequency")
    stream.average_amount_cents = _money_to_cents(_nested_amount(payload.get("average_amount")))
    stream.last_amount_cents = _optional_money_to_cents(_nested_amount(payload.get("last_amount")))
    stream.first_date = _optional_date_to_string(payload.get("first_date"))
    stream.last_date = _optional_date_to_string(payload.get("last_date"))
    stream.next_expected_date = _optional_date_to_string(payload.get("predicted_next_date"))
    stream.is_active = 1 if payload.get("is_active", True) else 0
    stream.raw_json = json.dumps(payload, separators=(",", ":"), default=str)
    stream.updated_at = now


def _create_net_worth_snapshot(db: Session, user_id: str) -> NetWorthSnapshot:
    now = utcnow()
    as_of_date = datetime.now(UTC).date().isoformat()
    accounts = db.query(Account).filter(Account.user_id == user_id, Account.is_active == 1).all()

    cash_cents = sum(_asset_value(account) for account in accounts if account.type in {"depository"})
    investments_cents = sum(_asset_value(account) for account in accounts if account.type in {"investment"})
    retirement_cents = sum(
        _asset_value(account)
        for account in accounts
        if account.subtype in {"401k", "ira", "roth", "roth ira", "retirement"}
    )
    credit_cards_cents = sum(_debt_value(account) for account in accounts if account.type == "credit")
    loans_cents = sum(_debt_value(account) for account in accounts if account.type == "loan")
    assets_cents = sum(_asset_value(account) for account in accounts)
    debts_cents = sum(_debt_value(account) for account in accounts)
    net_worth_cents = assets_cents - debts_cents

    snapshot = (
        db.query(NetWorthSnapshot)
        .filter(NetWorthSnapshot.user_id == user_id, NetWorthSnapshot.as_of_date == as_of_date)
        .one_or_none()
    )
    if snapshot is None:
        snapshot = NetWorthSnapshot(
            id=new_id(),
            user_id=user_id,
            as_of_date=as_of_date,
            created_at=now,
            assets_cents=0,
            debts_cents=0,
            net_worth_cents=0,
        )
        db.add(snapshot)

    snapshot.assets_cents = assets_cents
    snapshot.debts_cents = debts_cents
    snapshot.net_worth_cents = net_worth_cents
    snapshot.cash_cents = cash_cents
    snapshot.investments_cents = investments_cents
    snapshot.retirement_cents = retirement_cents
    snapshot.loans_cents = loans_cents
    snapshot.credit_cards_cents = credit_cards_cents
    return snapshot


def _money_to_cents(value: object) -> int:
    if value is None:
        return 0
    try:
        return int((Decimal(str(value)) * Decimal("100")).quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        return 0


def _optional_money_to_cents(value: object) -> int | None:
    if value is None:
        return None
    return _money_to_cents(value)


def _date_to_string(value: object) -> str:
    return _optional_date_to_string(value) or datetime.now(UTC).date().isoformat()


def _optional_date_to_string(value: object) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _legacy_category(payload: dict[str, Any], index: int) -> str | None:
    categories = payload.get("category") or []
    if isinstance(categories, list) and len(categories) > index:
        return str(categories[index])
    return None


def _nested_amount(value: object) -> object:
    if isinstance(value, dict):
        return value.get("amount")
    return value


def _classify_account(account_type: object, subtype: object) -> str:
    del subtype
    if account_type in {"credit", "loan"}:
        return "debt"
    return "asset"


def _asset_value(account: Account) -> int:
    return account.current_balance_cents if account.classification == "asset" else 0


def _debt_value(account: Account) -> int:
    return abs(account.current_balance_cents) if account.classification == "debt" else 0
