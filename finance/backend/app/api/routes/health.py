from fastapi import APIRouter

from app.core.config import get_settings


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, object]:
    settings = get_settings()
    return {
        "ok": True,
        "service": "taskbrain-finance",
        "environment": settings.env,
        "secure_config_present": settings.is_securely_configured,
        "openai_key_configured": bool(settings.openai_api_key),
        "plaid_configured": settings.plaid_configured,
        "plaid_environment": settings.normalized_plaid_env,
        "plaid_production_secret_present": bool(settings.plaid_production_secret),
        "plaid_production_linking_enabled": settings.plaid_allow_production_linking,
        "plaid_production_locked": settings.plaid_production_locked,
        "plaid_linking_enabled": settings.plaid_linking_enabled,
    }
