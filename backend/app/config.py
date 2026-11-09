from pathlib import Path

from pydantic import ValidationInfo, field_validator
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

    @field_validator("gemini_model", "scoring_engine", mode="after")
    @classmethod
    def _tolak_string_kosong(cls, v: str, info: ValidationInfo) -> str:
        """Variabel environment yang tidak diset tapi tetap diteruskan tiba
        sebagai string kosong, bukan sebagai tidak-ada, sehingga ia menimpa
        default di atas alih-alih membiarkannya. `GEMINI_MODEL: ${GEMINI_MODEL}`
        di compose adalah jalur persisnya: hasilnya scoring memanggil model
        bernama "" dan setiap proposal menggantung di scoring_status=failed
        sementara container melaporkan dirinya sehat."""
        if not v.strip():
            raise ValueError(
                f"{info.field_name} diset ke string kosong; biarkan variabelnya "
                "tidak diset kalau ingin memakai default, jangan diteruskan kosong"
            )
        return v

    gemini_timeout_s: int = 60
    # Review keamanan Finding 2: tanpa batas ini, setiap proposal yang
    # diterima langsung memicu job scoring tanpa batas konkurensi apa pun
    # (app/api/v1/proposals.py), dan BackgroundTasks milik FastAPI tidak
    # memberi batas sendiri -- sebanyak apa pun request bersamaan, sebanyak
    # itu pula panggilan Gemini konkuren. Angka kecil sengaja: proyek ini
    # satu container (D-01), bukan armada worker.
    scoring_max_concurrent_jobs: int = 3
    # Batas kasar ukuran prompt sebelum dikirim ke Gemini (app/ai/gemini_engine.py).
    # Dihitung dari panjang isi proposal yang dirakit, bukan dari batas
    # panjang per-field skema (app/schemas/proposal.py) -- field itu
    # membatasi satu kolom, ini membatasi gabungan ketiganya yang benar-
    # benar dikirim ke model.
    gemini_max_prompt_chars: int = 12_000
    # Kuota harian kasar, gagal tertutup (menolak memanggil, bukan diam-diam
    # melewatinya) begitu tercapai. Lihat docstring _DailyBudget di
    # gemini_engine.py untuk alasan lengkap kenapa ini ada DI SAMPING rate
    # limit per-IP/akun, bukan menggantikannya.
    gemini_daily_budget: int = 200


settings = Settings()
