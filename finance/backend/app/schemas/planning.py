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


class FinancialGoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    target_date: str | None = Field(default=None, min_length=10, max_length=10)
    target_amount_cents: int | None = Field(default=None, gt=0)
    priority: str = Field(default="medium", min_length=3, max_length=20)
    notes: str | None = Field(default=None, max_length=700)


class FinancialGoalResponse(BaseModel):
    id: str
    title: str
    target_date: str | None = None
    target_amount_cents: int | None = None
    priority: str
    status: str
    notes: str | None = None
    created_at: str
    updated_at: str


class FinancialGoalListResponse(BaseModel):
    goals: list[FinancialGoalResponse]
