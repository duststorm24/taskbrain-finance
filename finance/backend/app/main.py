from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ai, auth, budget, cash_flow, debt, health, investments, net_worth, plaid, planning, sync
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_runtime_security()
    app = FastAPI(title="TaskBrain Finance API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api/finance", tags=["health"])
    app.include_router(auth.router, prefix="/api/finance/auth", tags=["auth"])
    app.include_router(plaid.router, prefix="/api/finance/plaid", tags=["plaid"])
    app.include_router(sync.router, prefix="/api/finance/sync", tags=["sync"])
    app.include_router(planning.router, prefix="/api/finance/planning", tags=["planning"])
    app.include_router(net_worth.router, prefix="/api/finance/net-worth", tags=["net-worth"])
    app.include_router(cash_flow.router, prefix="/api/finance/cash-flow", tags=["cash-flow"])
    app.include_router(debt.router, prefix="/api/finance/debt", tags=["debt"])
    app.include_router(investments.router, prefix="/api/finance/investments", tags=["investments"])
    app.include_router(budget.router, prefix="/api/finance/budget", tags=["budget"])
    app.include_router(ai.router, prefix="/api/finance/ai", tags=["ai"])

    return app


app = create_app()
