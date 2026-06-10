from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.security import new_id, utcnow
from app.db.models import AccessReview, AccessReviewUser, AuditEvent, User
from app.db.session import get_db
from app.schemas.security import (
    AccessReviewCompleteRequest,
    AccessReviewCreateRequest,
    AccessReviewListResponse,
    AccessReviewResponse,
    AccessReviewUserResponse,
    AuditEventListResponse,
    AuditEventResponse,
)
from app.services.audit_log import log_event


router = APIRouter()


@router.get("/audit-events", response_model=AuditEventListResponse)
def list_audit_events(
    limit: int = 50,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AuditEventListResponse:
    _require_owner(user)
    bounded_limit = min(max(limit, 1), 200)
    rows = db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(bounded_limit).all()
    return AuditEventListResponse(events=[AuditEventResponse.model_validate(row) for row in rows])


@router.get("/access-reviews", response_model=AccessReviewListResponse)
def list_access_reviews(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AccessReviewListResponse:
    _require_owner(user)
    rows = db.query(AccessReview).order_by(AccessReview.created_at.desc()).limit(20).all()
    return AccessReviewListResponse(reviews=[_review_response(db, row) for row in rows])


@router.post("/access-reviews", response_model=AccessReviewResponse)
def create_access_review(
    payload: AccessReviewCreateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AccessReviewResponse:
    _require_owner(user)
    now = utcnow()
    today = datetime.now(UTC).date()
    period_end = payload.period_end or today.isoformat()
    period_start = payload.period_start or (today - timedelta(days=90)).isoformat()
    review = AccessReview(
        id=new_id(),
        owner_user_id=user.id,
        period_start=period_start,
        period_end=period_end,
        status="open",
        notes=payload.notes,
        created_at=now,
    )
    db.add(review)
    db.flush()

    users = db.query(User).order_by(User.created_at.asc()).all()
    for reviewed_user in users:
        db.add(
            AccessReviewUser(
                id=new_id(),
                review_id=review.id,
                user_id=reviewed_user.id,
                email=reviewed_user.email,
                display_name=reviewed_user.display_name,
                role=reviewed_user.role,
                status=reviewed_user.status,
                mfa_enabled=reviewed_user.mfa_enabled,
                last_login_at=reviewed_user.last_login_at,
                decision="pending",
                created_at=now,
                updated_at=now,
            )
        )
    log_event(
        db,
        action="access_review.created",
        actor_user_id=user.id,
        metadata={"review_id": review.id, "user_count": len(users), "period_start": period_start, "period_end": period_end},
    )
    db.commit()
    db.refresh(review)
    return _review_response(db, review)


@router.post("/access-reviews/{review_id}/complete", response_model=AccessReviewResponse)
def complete_access_review(
    review_id: str,
    payload: AccessReviewCompleteRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AccessReviewResponse:
    _require_owner(user)
    review = db.query(AccessReview).filter(AccessReview.id == review_id).one_or_none()
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access review not found")
    if review.status == "completed":
        return _review_response(db, review)

    now = utcnow()
    entries = db.query(AccessReviewUser).filter(AccessReviewUser.review_id == review.id).all()
    for entry in entries:
        if entry.decision == "pending":
            entry.decision = "disabled" if entry.status == "disabled" else "approved"
            entry.updated_at = now
    review.status = "completed"
    review.completed_at = now
    review.notes = payload.notes or review.notes
    log_event(
        db,
        action="access_review.completed",
        actor_user_id=user.id,
        metadata={"review_id": review.id, "user_count": len(entries)},
    )
    db.commit()
    db.refresh(review)
    return _review_response(db, review)


def _review_response(db: Session, review: AccessReview) -> AccessReviewResponse:
    entries = (
        db.query(AccessReviewUser)
        .filter(AccessReviewUser.review_id == review.id)
        .order_by(AccessReviewUser.email.asc())
        .all()
    )
    response = AccessReviewResponse.model_validate(review)
    response.users = [AccessReviewUserResponse.model_validate(entry) for entry in entries]
    return response


def _require_owner(user: User) -> None:
    if user.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required")
