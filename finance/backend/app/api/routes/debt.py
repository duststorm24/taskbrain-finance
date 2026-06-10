from fastapi import APIRouter, Depends

from app.api.deps import current_user
from app.db.models import User


router = APIRouter()


@router.get("")
def debt(user: User = Depends(current_user)) -> dict[str, object]:
    return {"user_id": user.id, "accounts": [], "payoffScenarios": []}


@router.post("/payoff-scenarios")
def payoff_scenarios(user: User = Depends(current_user)) -> dict[str, object]:
    return {"user_id": user.id, "scenario": None}

