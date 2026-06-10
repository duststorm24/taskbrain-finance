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
        "plaid_configured": bool(settings.plaid_client_id and settings.plaid_secret),
    }

