# Fase 00. Fondasi

**Hasil:** `make up` menyalakan Postgres dan backend, `GET /health` mengembalikan `200` dengan
status koneksi database, dan `make check` lolos di repo kosong.

**Spec terkait:** [12-non-functional](../prd/12-non-functional.md), [10-api-contract](../prd/10-api-contract.md)

## Struktur file yang dibuat di fase ini

```
backend/
  app/
    __init__.py
    main.py            # bikin app, daftarkan router dan handler
    config.py          # Settings dari environment
    errors.py          # exception domain + handler bentuk error seragam
    db/
      __init__.py
      session.py       # engine, get_session
    api/
      __init__.py
      v1/
        __init__.py
        health.py
  tests/
    conftest.py
    integration/test_health.py
  alembic/
  alembic.ini
  pyproject.toml
docker-compose.yml
Makefile
.env.example
.github/workflows/ci.yml
```

---

### Task 1: Health endpoint

**Files:**
- Create: `backend/app/main.py`, `backend/app/api/v1/health.py`, `backend/app/db/session.py`, `backend/app/config.py`
- Create: `backend/pyproject.toml`, `docker-compose.yml`, `.env.example`
- Test: `backend/tests/integration/test_health.py`, `backend/tests/conftest.py`

**Interfaces:**
- Consumes: tidak ada
- Produces: `app.main.create_app() -> FastAPI`, `app.config.Settings`, `app.db.session.get_session() -> AsyncGenerator[AsyncSession, None]`

- [ ] **Step 1: Siapkan Postgres dan dependency**

`docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: logicodix
      POSTGRES_PASSWORD: logicodix
      POSTGRES_DB: logicodix
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U logicodix"]
      interval: 2s
      retries: 15
  db-test:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: logicodix
      POSTGRES_PASSWORD: logicodix
      POSTGRES_DB: logicodix_test
    ports: ["5433:5432"]
    tmpfs: ["/var/lib/postgresql/data"]
```

`db-test` memakai `tmpfs` supaya test cepat dan datanya hilang saat container mati, dan terpisah
dari `db` supaya data dev tidak terhapus oleh test ([D-10](../docs/decisions.md)).

`backend/pyproject.toml` dependency inti:

```toml
[project]
name = "logicodix-backend"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115", "uvicorn[standard]>=0.32", "sqlmodel>=0.0.22",
  "asyncpg>=0.30", "alembic>=1.14", "pydantic-settings>=2.6",
  "argon2-cffi>=23.1", "pyjwt>=2.10",
  "instructor>=1.7", "google-genai>=0.8",
]

[project.optional-dependencies]
dev = ["pytest>=8.3", "pytest-asyncio>=0.24", "httpx>=0.28", "ruff>=0.8", "mypy>=1.13"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = ["live: memanggil Gemini sungguhan, di-skip default"]
```

- [ ] **Step 2: Tulis test yang gagal**

`backend/tests/integration/test_health.py`:

```python
async def test_health_mengembalikan_status_database(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}
```

`backend/tests/conftest.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import create_app

@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

- [ ] **Step 3: Jalankan test, pastikan gagal**

Run: `docker compose up -d db-test && cd backend && pytest tests/integration/test_health.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 4: Implementasi minimal**

`backend/app/config.py`:

```python
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
```

`backend/app/db/session.py`:

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
```

`backend/app/api/v1/health.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session

router = APIRouter(tags=["health"])

@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
```

`backend/app/main.py`:

```python
from fastapi import FastAPI
from app.api.v1 import health

def create_app() -> FastAPI:
    app = FastAPI(title="Logicodix API", version="0.1.0")
    app.include_router(health.router)
    return app

app = create_app()
```

- [ ] **Step 5: Jalankan test, pastikan lolos**

Run: `cd backend && pytest tests/integration/test_health.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend docker-compose.yml
git commit -m "feat: scaffold FastAPI backend with health endpoint"
```

---

### Task 2: Bentuk error yang seragam

**Files:**
- Create: `backend/app/errors.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/integration/test_error_shape.py`

**Interfaces:**
- Produces: `DomainError(code, message, status, detail)`, `ConflictError`, `ForbiddenError`,
  `NotFoundError`, `UnprocessableError` — semua dipakai oleh seluruh service di fase berikutnya.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_error_shape.py
import pytest
from app.errors import ConflictError

async def test_domain_error_jadi_bentuk_seragam(client, app):
    @app.get("/_boom")
    async def boom():
        raise ConflictError("transisi_tidak_sah", "Proposal sudah funded.",
                            detail={"current_status": "funded"})

    res = await client.get("/_boom")
    assert res.status_code == 409
    assert res.json() == {
        "error": {
            "code": "transisi_tidak_sah",
            "message": "Proposal sudah funded.",
            "detail": {"current_status": "funded"},
        }
    }
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_error_shape.py -v`
Expected: FAIL dengan `ImportError: cannot import name 'ConflictError'`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/errors.py
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

class DomainError(Exception):
    status = 400

    def __init__(self, code: str, message: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail or {}

class NotFoundError(DomainError):
    status = 404

class ForbiddenError(DomainError):
    status = 403

class ConflictError(DomainError):
    """Transisi status tidak sah, atau aturan bisnis dilanggar."""
    status = 409

class UnprocessableError(DomainError):
    status = 422

def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"error": {"code": exc.code, "message": exc.message, "detail": exc.detail}},
        )
```

Lalu panggil `register_error_handlers(app)` di `create_app()`.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_error_shape.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add uniform error envelope for all endpoints"
```

---

### Task 3: Alembic dan fixture database

**Files:**
- Create: `backend/alembic.ini`, `backend/alembic/env.py`
- Modify: `backend/tests/conftest.py`
- Test: `backend/tests/integration/test_db_fixture.py`

**Interfaces:**
- Produces: fixture `db` (session yang di-rollback), fixture `client` yang memakai `db` yang sama.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_db_fixture.py
from sqlalchemy import text

async def test_fixture_db_dirollback_antar_test(db):
    await db.execute(text("CREATE TEMP TABLE jejak (n int)"))
    await db.execute(text("INSERT INTO jejak VALUES (1)"))
    rows = (await db.execute(text("SELECT count(*) FROM jejak"))).scalar()
    assert rows == 1

async def test_fixture_db_bersih_di_test_berikutnya(db):
    exists = (await db.execute(
        text("SELECT to_regclass('pg_temp.jejak') IS NOT NULL")
    )).scalar()
    assert exists is False
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_db_fixture.py -v`
Expected: FAIL dengan `fixture 'db' not found`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/tests/conftest.py (tambahan)
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import engine, get_session
from app.main import create_app

@pytest.fixture
async def db():
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()

@pytest.fixture
async def app(db):
    application = create_app()
    application.dependency_overrides[get_session] = lambda: db
    return application
```

`client` diubah agar memakai fixture `app` di atas, bukan membuat app sendiri.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/ -v`
Expected: PASS, keduanya

- [ ] **Step 5: Jalankan migrasi kosong**

```bash
cd backend && alembic revision -m "awal" && alembic upgrade head
```

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: set up alembic and rolled-back database fixtures"
```

---

### Task 4: Makefile dan CI

**Files:**
- Create: `Makefile`, `.github/workflows/ci.yml`

- [ ] **Step 1: Tulis Makefile**

```makefile
.PHONY: up down migrate test test-unit test-regression test-live test-fe test-e2e check demo

up:              ; docker compose up -d db db-test && cd backend && uvicorn app.main:app --reload
down:            ; docker compose down
migrate:         ; cd backend && alembic upgrade head
test:            ; cd backend && pytest tests/unit tests/integration tests/regression -q
test-unit:       ; cd backend && pytest tests/unit -q
test-regression: ; cd backend && pytest tests/regression -q
test-live:       ; cd backend && pytest tests/contract -m live -v
test-fe:         ; cd frontend && npm run test
test-e2e:        ; cd frontend && npx playwright test
check:           ; cd backend && ruff check . && mypy app && cd ../frontend && npx tsc --noEmit && npm run lint
	$(MAKE) test
	$(MAKE) test-fe
demo:            ; SCORING_ENGINE=mock $(MAKE) up
```

- [ ] **Step 2: Tulis workflow CI**

```yaml
# .github/workflows/ci.yml
name: ci
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: logicodix
          POSTGRES_PASSWORD: logicodix
          POSTGRES_DB: logicodix_test
        ports: ["5433:5432"]
        options: >-
          --health-cmd "pg_isready -U logicodix" --health-interval 2s --health-retries 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e "backend[dev]"
      - run: cd backend && alembic upgrade head
      - run: cd backend && ruff check . && mypy app
      - run: cd backend && pytest tests/unit tests/integration tests/regression -q
```

CI tidak menjalankan `tests/contract` karena butuh API key dan jaringan.

- [ ] **Step 3: Jalankan dan pastikan hijau**

Run: `make check`
Expected: lolos (frontend belum ada, bagian frontend di-skip sampai fase 10)

- [ ] **Step 4: Commit**

```bash
git add Makefile .github
git commit -m "chore: add Makefile and CI workflow"
```

---

### Task 5: Log terstruktur

**Files:**
- Create: `backend/app/logging.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/integration/test_logging.py`

Cukup untuk menjelaskan kegagalan saat demo, tidak lebih
([12-non-functional](../prd/12-non-functional.md)). Yang penting di sini bukan kelengkapannya,
melainkan satu hal yang tidak boleh ikut tercatat.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_logging.py
import json

async def test_setiap_request_menghasilkan_satu_baris_json(client, caplog):
    await client.get("/health")
    baris = [json.loads(r.message) for r in caplog.records if r.name == "logicodix.http"]
    assert len(baris) == 1
    assert baris[0].keys() >= {"method", "path", "status", "durasi_ms"}

async def test_log_memuat_user_id_untuk_request_terautentikasi(client, investor, caplog):
    await client.get("/api/v1/auth/me", headers=investor.headers)
    baris = [json.loads(r.message) for r in caplog.records if r.name == "logicodix.http"]
    assert baris[0]["user_id"] == str(investor.user.id)

async def test_log_tidak_pernah_memuat_password_atau_token(client, caplog):
    await client.post("/api/v1/auth/login",
                      json={"email": "a@contoh.id", "password": "rahasia123"})
    teks = " ".join(r.message for r in caplog.records)
    assert "rahasia123" not in teks
    assert "Bearer " not in teks

async def test_log_pemanggilan_ai_tidak_memuat_isi_proposal(db, submitted_proposal,
                                                            engine_mock, clock, caplog):
    from app.services.scoring import jalankan_scoring
    await jalankan_scoring(db, submitted_proposal.id, engine_mock, clock)
    baris = [json.loads(r.message) for r in caplog.records if r.name == "logicodix.ai"]
    assert baris[0].keys() >= {"model", "durasi_ms", "valid"}
    assert submitted_proposal.business_profile not in " ".join(
        r.message for r in caplog.records)
```

Dua test terakhir yang sebenarnya penting. Password di log dan isi proposal di log keduanya adalah
kebocoran yang tidak pernah melempar error dan baru ketahuan saat sudah terlambat.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_logging.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/logging.py
import json
import logging
import time
from fastapi import Request

http_log = logging.getLogger("logicodix.http")
ai_log = logging.getLogger("logicodix.ai")

async def catat_request(request: Request, call_next):
    mulai = time.perf_counter()
    respons = await call_next(request)
    http_log.info(json.dumps({
        "method": request.method,
        "path": request.url.path,
        "status": respons.status_code,
        "durasi_ms": round((time.perf_counter() - mulai) * 1000),
        "user_id": getattr(request.state, "user_id", None),
    }))
    return respons
```

Yang dicatat untuk pemanggilan AI: model, durasi, jumlah token, dan apakah output lolos validasi.
Isi proposal tidak pernah ikut.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_logging.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add structured request logging without secrets"
```

## Gerbang keluar fase 00

- [ ] `make up` menyalakan Postgres dan backend
- [ ] `curl localhost:8000/health` mengembalikan `{"status":"ok","database":"ok"}`
- [ ] `make check` lolos
- [ ] Tidak ada API key atau rahasia yang ter-commit; `.env.example` hanya berisi nama variabel
- [ ] Log request berjalan, dan tidak memuat password, token, maupun isi proposal
