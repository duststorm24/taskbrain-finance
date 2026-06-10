from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import current_user
from app.core.config import get_settings
from app.db.models import User


router = APIRouter()


@router.get("/summaries")
def summaries(user: User = Depends(current_user)) -> dict[str, object]:
    return {"user_id": user.id, "summaries": []}


@router.post("/summaries/daily")
def daily_summary(user: User = Depends(current_user)) -> dict[str, object]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OpenAI API key is not configured")
    return {"user_id": user.id, "status": "queued"}

