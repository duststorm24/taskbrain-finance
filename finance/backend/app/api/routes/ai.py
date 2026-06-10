import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import get_settings
from app.db.models import AiSummary, User
from app.db.session import get_db
from app.schemas.ai import AiAnalysisRequest, AiSummaryListResponse, AiSummaryResponse
from app.services.ai_service import generate_analysis, list_ai_summaries


router = APIRouter()


@router.get("/summaries", response_model=AiSummaryListResponse)
def summaries(user: User = Depends(current_user), db: Session = Depends(get_db)) -> AiSummaryListResponse:
    return AiSummaryListResponse(summaries=[_response(row) for row in list_ai_summaries(db, user.id)])


@router.post("/analyze", response_model=AiSummaryResponse)
def analyze(
    payload: AiAnalysisRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AiSummaryResponse:
    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OpenAI API key is not configured")
    try:
        summary = generate_analysis(db, user, payload.mode)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"OpenAI analysis failed: {exc}") from exc
    return _response(summary)


@router.post("/summaries/daily", response_model=AiSummaryResponse)
def daily_summary(user: User = Depends(current_user), db: Session = Depends(get_db)) -> AiSummaryResponse:
    return analyze(AiAnalysisRequest(mode="daily"), user, db)


def _response(summary: AiSummary) -> AiSummaryResponse:
    try:
        insights = json.loads(summary.insights_json)
    except json.JSONDecodeError:
        insights = {}
    return AiSummaryResponse(
        id=summary.id,
        summary_type=summary.summary_type,
        period_start=summary.period_start,
        period_end=summary.period_end,
        model=summary.model,
        title=summary.title,
        summary_markdown=summary.summary_markdown,
        insights=insights,
        input_fingerprint=summary.input_fingerprint,
        created_at=summary.created_at,
    )
