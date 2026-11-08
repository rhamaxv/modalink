from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute, not relative: Makefile targets and CI steps invoke this process with
# cwd set to backend/, while the single .env lives at the repo root next to
# docker-compose.yml, which is where `docker compose` itself reads it from.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    env: str = "dev"
    # No default: a missing value must fail startup loudly instead of silently
    # pointing at a database, secret, or key nobody configured.
    database_url: str
    jwt_secret: str
    jwt_ttl_hours: int = 24
    scoring_engine: str = "mock"      # "mock" atau "gemini"
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_s: int = 20


settings = Settings()
