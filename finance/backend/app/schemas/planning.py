from pydantic import BaseModel, Field


class PlannedExpenseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    due_date: str = Field(min_length=10, max_length=10)
    amount_cents: int = Field(gt=0)
    category: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=500)


class PlannedExpenseResponse(BaseModel):
    id: str
    title: str
    due_date: str
    amount_cents: int
    category: str | None = None
    notes: str | None = None
    created_at: str
    updated_at: str


class PlannedExpenseListResponse(BaseModel):
    expenses: list[PlannedExpenseResponse]

