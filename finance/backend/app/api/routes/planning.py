from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.security import new_id, utcnow
from app.db.models import PlannedExpense, User
from app.db.session import get_db
from app.schemas.planning import PlannedExpenseCreate, PlannedExpenseListResponse, PlannedExpenseResponse


router = APIRouter()


@router.get("/expenses", response_model=PlannedExpenseListResponse)
def list_expenses(user: User = Depends(current_user), db: Session = Depends(get_db)) -> PlannedExpenseListResponse:
    rows = (
        db.query(PlannedExpense)
        .filter(PlannedExpense.user_id == user.id)
        .order_by(PlannedExpense.due_date.asc(), PlannedExpense.created_at.asc())
        .all()
    )
    return PlannedExpenseListResponse(expenses=[_response(row) for row in rows])


@router.post("/expenses", response_model=PlannedExpenseResponse)
def create_expense(
    payload: PlannedExpenseCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PlannedExpenseResponse:
    now = utcnow()
    expense = PlannedExpense(
        id=new_id(),
        user_id=user.id,
        title=payload.title,
        due_date=payload.due_date,
        amount_cents=payload.amount_cents,
        category=payload.category,
        notes=payload.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return _response(expense)


@router.delete("/expenses/{expense_id}")
def delete_expense(
    expense_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    expense = (
        db.query(PlannedExpense)
        .filter(PlannedExpense.id == expense_id, PlannedExpense.user_id == user.id)
        .one_or_none()
    )
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planned expense not found")
    db.delete(expense)
    db.commit()
    return {"ok": True}


def _response(expense: PlannedExpense) -> PlannedExpenseResponse:
    return PlannedExpenseResponse(
        id=expense.id,
        title=expense.title,
        due_date=expense.due_date,
        amount_cents=expense.amount_cents,
        category=expense.category,
        notes=expense.notes,
        created_at=expense.created_at,
        updated_at=expense.updated_at,
    )

