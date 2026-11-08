from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+asyncpg://logicodix:logicodix@localhost:5433/logicodix_test"
    jwt_secret: str = "ganti-di-produksi"
    jwt_ttl_hours: int = 24
    scoring_engine: str = "mock"      # "mock" atau "gemini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_s: int = 20


settings = Settings()
