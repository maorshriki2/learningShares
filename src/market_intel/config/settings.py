from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    sec_user_agent: str = Field(
        default="MarketIntelBot/1.0 (contact@example.com)",
        validation_alias="SEC_USER_AGENT",
    )
    redis_url: str | None = Field(default=None, validation_alias="REDIS_URL")

    polygon_api_key: str | None = Field(default=None, validation_alias="POLYGON_API_KEY")
    finnhub_api_key: str | None = Field(default=None, validation_alias="FINNHUB_API_KEY")

    api_host: str = Field(default="127.0.0.1", validation_alias="API_HOST")
    api_port: int = Field(default=8000, validation_alias="API_PORT")
    api_public_url: HttpUrl = Field(
        default="http://127.0.0.1:8000",
        validation_alias="API_PUBLIC_URL",
    )

    streamlit_server_port: int = Field(default=8501, validation_alias="STREAMLIT_SERVER_PORT")

    portfolio_storage_path: str = Field(
        default="data/portfolio.json",
        validation_alias="PORTFOLIO_STORAGE_PATH",
    )

    cache_ttl_seconds: int = Field(default=300, validation_alias="CACHE_TTL_SECONDS")
    http_timeout_seconds: float = Field(default=30.0, validation_alias="HTTP_TIMEOUT_SECONDS")
    finbert_model_name: str = Field(
        default="ProsusAI/finbert",
        validation_alias="FINBERT_MODEL_NAME",
    )

    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-3-5-haiku-20241022",
        validation_alias="ANTHROPIC_MODEL",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
