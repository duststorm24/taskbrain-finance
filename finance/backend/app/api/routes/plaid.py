import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import get_settings
from app.core.encryption import encrypt_secret
from app.core.security import new_id, utcnow
from app.db.models import User
from app.db.models import PlaidItem
from app.db.session import get_db
from app.schemas.plaid import ExchangePublicTokenRequest, LinkTokenResponse, PlaidItemListResponse, PlaidItemResponse
from app.services.plaid_service import create_link_token, exchange_public_token_for_item


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
    settings = get_settings()
    if not settings.plaid_configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Plaid is not configured")
    return LinkTokenResponse(link_token=create_link_token(user.id))


@router.post("/exchange-public-token", response_model=PlaidItemResponse)
def exchange_public_token(
    payload: ExchangePublicTokenRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PlaidItemResponse:
    settings = get_settings()
    if settings.plaid_env != "sandbox":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Plaid sandbox is enabled for MVP setup")
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
