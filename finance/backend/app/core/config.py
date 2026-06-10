from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_prefix="TASKBRAIN_FINANCE_",
        extra="ignore",
    )

    env: str = "development"
    database_url: str = "sqlite:///./data/finance.db"
    allowed_origins: str = "http://localhost:8080,http://127.0.0.1:8080"
    session_secret: str = Field(default="replace-with-random-session-secret")
    token_encryption_key: str = Field(default="replace-with-fernet-key")

    plaid_env: str = Field(default="sandbox", validation_alias="PLAID_ENV")
    plaid_client_id: str = Field(default="", validation_alias="PLAID_CLIENT_ID")
    plaid_secret: str = Field(default="", validation_alias="PLAID_SECRET")
    plaid_sandbox_secret: str = Field(default="", validation_alias="PLAID_SANDBOX_SECRET")
    plaid_production_secret: str = Field(default="", validation_alias="PLAID_PRODUCTION_SECRET")
    plaid_allow_production_linking: bool = Field(default=False, validation_alias="PLAID_ALLOW_PRODUCTION_LINKING")
    plaid_products: str = Field(default="transactions", validation_alias="PLAID_PRODUCTS")
    plaid_optional_products: str = Field(default="investments,liabilities", validation_alias="PLAID_OPTIONAL_PRODUCTS")

    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5.5", validation_alias="OPENAI_MODEL")
    openai_daily_model: str = Field(default="", validation_alias="OPENAI_DAILY_MODEL")
    openai_detailed_model: str = Field(default="", validation_alias="OPENAI_DETAILED_MODEL")
    openai_complete_model: str = Field(default="", validation_alias="OPENAI_COMPLETE_MODEL")
    inactive_user_disable_days: int = Field(default=90, validation_alias="TASKBRAIN_FINANCE_INACTIVE_USER_DISABLE_DAYS")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def is_securely_configured(self) -> bool:
        return (
            self.session_secret != "replace-with-random-session-secret"
            and self.token_encryption_key != "replace-with-fernet-key"
        )

    @property
    def cookie_secure(self) -> bool:
        return self.env.lower() not in {"development", "local", "test"}

    @property
    def normalized_plaid_env(self) -> str:
        return self.plaid_env.lower().strip()

    @property
    def active_plaid_secret(self) -> str:
        if self.normalized_plaid_env == "production":
            return self.plaid_production_secret or self.plaid_secret
        return self.plaid_sandbox_secret or self.plaid_secret

    @property
    def plaid_configured(self) -> bool:
        return bool(self.plaid_client_id and self.active_plaid_secret)

    @property
    def plaid_production_locked(self) -> bool:
        return self.normalized_plaid_env == "production" and not self.plaid_allow_production_linking

    @property
    def plaid_linking_enabled(self) -> bool:
        return self.plaid_configured and not self.plaid_production_locked

    def openai_model_for_mode(self, mode: str) -> str:
        if mode == "daily":
            return self.openai_daily_model or "gpt-5.4-mini"
        if mode == "detailed":
            return self.openai_detailed_model or self.openai_model
        if mode == "complete":
            return self.openai_complete_model or self.openai_model
        return self.openai_model

    def validate_runtime_security(self) -> None:
        if not self.is_securely_configured:
            raise RuntimeError(
                "TaskBrain Finance requires TASKBRAIN_FINANCE_SESSION_SECRET and "
                "TASKBRAIN_FINANCE_TOKEN_ENCRYPTION_KEY to be set before startup."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
