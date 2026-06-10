from pydantic import BaseModel, Field


class LinkTokenResponse(BaseModel):
    link_token: str


class ExchangePublicTokenRequest(BaseModel):
    public_token: str = Field(min_length=1)


class PlaidItemResponse(BaseModel):
    item_id: str
    status: str
    created_at: str | None = None
    last_successful_sync_at: str | None = None


class PlaidItemListResponse(BaseModel):
    items: list[PlaidItemResponse]
