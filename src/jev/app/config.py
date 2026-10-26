"""Global settings, loaded once from the project's .env file.

Every module imports `settings` from here instead of reading environment
variables itself, so configuration lives in exactly one place.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# src/jev/app/config.py -> parents[3] is the project root where .env lives
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # Field names map to env vars case-insensitively: OPENROUTER_API_KEY -> openrouter_api_key
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    openrouter_api_key: str
    # Pin a version when you rely on thresholds; "~typesafe/jev-latest" can change under you
    jev_model: str = "typesafe/jev-1.14"
    openrouter_base_url: str = "https://openrouter.ai/api/alpha"
    request_timeout: float = 30.0

    # Where `uv run jev` serves the API
    host: str = "127.0.0.1"
    port: int = 8000


settings = Settings()
