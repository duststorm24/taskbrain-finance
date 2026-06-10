from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.security import new_id, utcnow
from app.db.models import FinancialGoal, PlannedExpense, User
from app.db.session import get_db
from app.schemas.planning import (
    FinancialGoalCreate,
    FinancialGoalListResponse,
    FinancialGoalResponse,
    PlannedExpenseCreate,
    PlannedExpenseListResponse,
    PlannedExpenseResponse,
)


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


@router.get("/goals", response_model=FinancialGoalListResponse)
def list_goals(user: User = Depends(current_user), db: Session = Depends(get_db)) -> FinancialGoalListResponse:
    rows = (
        db.query(FinancialGoal)
        .filter(FinancialGoal.user_id == user.id, FinancialGoal.status == "active")
        .order_by(FinancialGoal.target_date.asc(), FinancialGoal.created_at.asc())
        .all()
    )
    return FinancialGoalListResponse(goals=[_goal_response(row) for row in rows])


@router.post("/goals", response_model=FinancialGoalResponse)
def create_goal(
    payload: FinancialGoalCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> FinancialGoalResponse:
    now = utcnow()
    goal = FinancialGoal(
        id=new_id(),
        user_id=user.id,
        title=payload.title,
        target_date=payload.target_date,
        target_amount_cents=payload.target_amount_cents,
        priority=payload.priority,
        status="active",
        notes=payload.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _goal_response(goal)


@router.delete("/goals/{goal_id}")
def delete_goal(
    goal_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    goal = db.query(FinancialGoal).filter(FinancialGoal.id == goal_id, FinancialGoal.user_id == user.id).one_or_none()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial goal not found")
    goal.status = "archived"
    goal.updated_at = utcnow()
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


def _goal_response(goal: FinancialGoal) -> FinancialGoalResponse:
    return FinancialGoalResponse(
        id=goal.id,
        title=goal.title,
        target_date=goal.target_date,
        target_amount_cents=goal.target_amount_cents,
        priority=goal.priority,
        status=goal.status,
        notes=goal.notes,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )
