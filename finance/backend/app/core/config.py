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
    plaid_products: str = Field(default="transactions", validation_alias="PLAID_PRODUCTS")
    plaid_optional_products: str = Field(default="investments,liabilities", validation_alias="PLAID_OPTIONAL_PRODUCTS")

    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5.5", validation_alias="OPENAI_MODEL")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def is_securely_configured(self) -> bool:
        return (
            self.session_secret != "replace-with-random-session-secret"
            and self.token_encryption_key != "replace-with-fernet-key"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

