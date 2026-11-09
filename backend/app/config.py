from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute, not relative: Makefile targets and CI steps invoke this process with
# cwd set to backend/, while the single .env lives at the repo root next to
# docker-compose.yml, which is where `docker compose` itself reads it from.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    # Default "prod", bukan "dev", karena nilai ini memagari router internal
    # (BR-63) dan salah satu endpoint di baliknya memajukan jam global tanpa
    # autentikasi apa pun: satu request anonim menggagalkan setiap proposal
    # yang tenggatnya lewat dan merefund setiap pledge aktif, untuk semua
    # pengguna, permanen. Default yang permisif berarti deployment mana pun
    # yang lupa menyetel ENV membuka itu ke internet. Gagal ke arah tertutup.
    env: str = "prod"
    # No default: a missing value must fail startup loudly instead of silently
    # pointing at a database, secret, or key nobody configured.
    database_url: str
    jwt_secret: str
    jwt_ttl_hours: int = 24
    scoring_engine: str = "mock"  # "mock" atau "gemini"
    # No default placeholder either: only GeminiEngine (phase 05) reads this,
    # and mock mode never does, so leaving it unset must not block startup.
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_s: int = 60


settings = Settings()
