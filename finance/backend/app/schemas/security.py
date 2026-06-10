from pydantic import BaseModel, ConfigDict, Field


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_user_id: str | None
    target_user_id: str | None
    action: str
    outcome: str
    metadata_json: str
    created_at: str


class AuditEventListResponse(BaseModel):
    events: list[AuditEventResponse]


class AccessReviewUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    email: str
    display_name: str
    role: str
    status: str
    mfa_enabled: bool
    last_login_at: str | None
    decision: str
    notes: str | None


class AccessReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_user_id: str | None
    period_start: str
    period_end: str
    status: str
    notes: str | None
    created_at: str
    completed_at: str | None
    users: list[AccessReviewUserResponse] = []


class AccessReviewListResponse(BaseModel):
    reviews: list[AccessReviewResponse]


class AccessReviewCreateRequest(BaseModel):
    period_start: str | None = None
    period_end: str | None = None
    notes: str | None = Field(default=None, max_length=2000)


class AccessReviewCompleteRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)
