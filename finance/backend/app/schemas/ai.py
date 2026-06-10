from typing import Literal

from pydantic import BaseModel


AiAnalysisMode = Literal["daily", "detailed", "complete"]


class AiAnalysisRequest(BaseModel):
    mode: AiAnalysisMode


class AiSummaryResponse(BaseModel):
    id: str
    summary_type: str
    period_start: str
    period_end: str
    model: str
    title: str
    summary_markdown: str
    insights: dict[str, object]
    input_fingerprint: str
    created_at: str


class AiSummaryListResponse(BaseModel):
    summaries: list[AiSummaryResponse]
