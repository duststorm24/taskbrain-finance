import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import get_settings
from app.core.encryption import decrypt_secret, encrypt_secret
from app.core.security import new_id, utcnow
from app.db.models import (
    Account,
    AccountBalanceSnapshot,
    AiSummary,
    NetWorthSnapshot,
    PlaidItem,
    RecurringStream,
    SyncRun,
    Transaction,
    User,
)
from app.db.session import get_db
from app.schemas.plaid import ExchangePublicTokenRequest, LinkTokenResponse, PlaidItemListResponse, PlaidItemResponse
from app.services.plaid_service import create_link_token, exchange_public_token_for_item, remove_item


router = APIRouter()


@router.get("/items", response_model=PlaidItemListResponse)
def items(user: User = Depends(current_user), db: Session = Depends(get_db)) -> PlaidItemListResponse:
    rows = db.query(PlaidItem).filter(PlaidItem.user_id == user.id).order_by(PlaidItem.created_at.desc()).all()
    return PlaidItemListResponse(
        items=[
            PlaidItemResponse(
                item_id=row.id,
                status=row.status,
                created_at=row.created_at,
                last_successful_sync_at=row.last_successful_sync_at,
            )
            for row in rows
        ]
    )


@router.post("/link-token", response_model=LinkTokenResponse)
def link_token(user: User = Depends(current_user)) -> LinkTokenResponse:
    _require_mfa_for_plaid_link(user)
    settings = get_settings()
    if not settings.plaid_configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Plaid is not configured")
    if not settings.plaid_linking_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Plaid production linking is locked. Set PLAID_ALLOW_PRODUCTION_LINKING=true only when ready.",
        )
    return LinkTokenResponse(link_token=create_link_token(user.id))


@router.post("/exchange-public-token", response_model=PlaidItemResponse)
def exchange_public_token(
    payload: ExchangePublicTokenRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PlaidItemResponse:
    _require_mfa_for_plaid_link(user)
    settings = get_settings()
    if not settings.plaid_linking_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Plaid production linking is locked. Set PLAID_ALLOW_PRODUCTION_LINKING=true only when ready.",
        )
    item = exchange_public_token_for_item(user.id, payload.public_token)
    now = utcnow()
    plaid_item = PlaidItem(
        id=new_id(),
        user_id=user.id,
        plaid_item_id=item["item_id"],
        access_token_encrypted=encrypt_secret(item["access_token"]),
        products_json=json.dumps(item.get("products", [])),
        available_products_json=json.dumps(item.get("available_products", [])),
        status="active",
        created_at=now,
        updated_at=now,
    )
    db.add(plaid_item)
    db.commit()
    return PlaidItemResponse(item_id=plaid_item.id, status="stored")


@router.delete("/items/{item_id}", response_model=PlaidItemResponse)
def disconnect_item(
    item_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PlaidItemResponse:
    plaid_item = db.query(PlaidItem).filter(PlaidItem.id == item_id, PlaidItem.user_id == user.id).one_or_none()
    if plaid_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plaid item was not found")

    try:
        remove_item(decrypt_secret(plaid_item.access_token_encrypted))
    except Exception as exc:
        now = utcnow()
        plaid_item.status = "disconnect_failed"
        plaid_item.last_failed_sync_at = now
        plaid_item.last_error = str(exc)
        plaid_item.updated_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Plaid disconnect failed, so local financial data was not deleted.",
        ) from exc

    account_ids = [
        row.id
        for row in db.query(Account.id).filter(Account.user_id == user.id, Account.plaid_item_id == plaid_item.id).all()
    ]
    if account_ids:
        db.query(AccountBalanceSnapshot).filter(AccountBalanceSnapshot.account_id.in_(account_ids)).delete(
            synchronize_session=False
        )
        db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.account_id.in_(account_ids)).delete(
            synchronize_session=False
        )
        db.query(RecurringStream).filter(
            RecurringStream.user_id == user.id,
            RecurringStream.account_id.in_(account_ids),
        ).delete(synchronize_session=False)
        db.query(Account).filter(Account.user_id == user.id, Account.id.in_(account_ids)).delete(synchronize_session=False)

    db.query(NetWorthSnapshot).filter(NetWorthSnapshot.user_id == user.id).delete(synchronize_session=False)
    db.query(AiSummary).filter(AiSummary.user_id == user.id).delete(synchronize_session=False)
    db.query(SyncRun).filter(SyncRun.user_id == user.id).delete(synchronize_session=False)
    db.delete(plaid_item)
    db.commit()
    return PlaidItemResponse(item_id=item_id, status="disconnected")


def _require_mfa_for_plaid_link(user: User) -> None:
    if not user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enable account MFA before connecting financial institutions.",
        )
