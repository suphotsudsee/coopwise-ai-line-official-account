from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_log_level: str = "INFO"
    app_docs_enabled: bool = True

    internal_api_key: SecretStr = Field(min_length=32)

    line_channel_access_token: SecretStr
    line_channel_secret: SecretStr
    line_default_destination_user_id: str | None = None
    line_api_base_url: str = "https://api.line.me"
    line_request_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    line_max_retries: int = Field(default=2, ge=0, le=5)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
