from collections import defaultdict, deque
from time import monotonic

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse, Response

from app.api.routes import ai, auth, budget, cash_flow, debt, health, investments, net_worth, plaid, planning, security, sync
from app.core.config import get_settings


AUTH_RATE_LIMIT_PATHS = {
    "/api/finance/auth/login",
    "/api/finance/auth/register",
    "/api/finance/auth/mfa/setup",
    "/api/finance/auth/mfa/enable",
    "/api/finance/auth/mfa/disable",
}
RATE_LIMIT_WINDOW_SECONDS = 300
RATE_LIMIT_MAX_ATTEMPTS = 25
_rate_limit_attempts: dict[str, deque[float]] = defaultdict(deque)


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

    @app.middleware("http")
    async def security_middleware(request: Request, call_next) -> Response:  # noqa: ANN001
        if _is_rate_limited(request):
            return _with_security_headers(
                JSONResponse(
                    status_code=429,
                    content={"detail": "Too many authentication attempts. Wait a few minutes and try again."},
                )
            )
        response = await call_next(request)
        return _with_security_headers(response)

    app.include_router(health.router, prefix="/api/finance", tags=["health"])
    app.include_router(auth.router, prefix="/api/finance/auth", tags=["auth"])
    app.include_router(plaid.router, prefix="/api/finance/plaid", tags=["plaid"])
    app.include_router(sync.router, prefix="/api/finance/sync", tags=["sync"])
    app.include_router(planning.router, prefix="/api/finance/planning", tags=["planning"])
    app.include_router(security.router, prefix="/api/finance/security", tags=["security"])
    app.include_router(net_worth.router, prefix="/api/finance/net-worth", tags=["net-worth"])
    app.include_router(cash_flow.router, prefix="/api/finance/cash-flow", tags=["cash-flow"])
    app.include_router(debt.router, prefix="/api/finance/debt", tags=["debt"])
    app.include_router(investments.router, prefix="/api/finance/investments", tags=["investments"])
    app.include_router(budget.router, prefix="/api/finance/budget", tags=["budget"])
    app.include_router(ai.router, prefix="/api/finance/ai", tags=["ai"])

    return app


def _is_rate_limited(request: Request) -> bool:
    if request.method != "POST" or request.url.path not in AUTH_RATE_LIMIT_PATHS:
        return False
    client_host = request.client.host if request.client else "unknown"
    key = f"{client_host}:{request.url.path}"
    now = monotonic()
    attempts = _rate_limit_attempts[key]
    while attempts and now - attempts[0] > RATE_LIMIT_WINDOW_SECONDS:
        attempts.popleft()
    attempts.append(now)
    return len(attempts) > RATE_LIMIT_MAX_ATTEMPTS


def _with_security_headers(response: Response) -> Response:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


app = create_app()
