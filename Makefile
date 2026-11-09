.PHONY: up down migrate test test-unit test-regression test-live test-fe test-e2e check demo

# Local dev runs these targets without an activated venv, so tool names alone
# are not on PATH. Relative to backend/, since every use below follows a
# `cd backend &&`. CI never invokes make; it calls ruff, mypy, and pytest
# directly from its own environment, so this default only matters locally.
VENV_BIN ?= .venv/bin/

up:
	docker compose up -d db db-test
	cd backend && $(VENV_BIN)uvicorn app.main:app --reload

down:
	docker compose down

migrate:
	cd backend && $(VENV_BIN)alembic upgrade head

# `ls -d` lists only the test directories that already exist: tests/regression
# and tests/contract arrive in later phases, and pytest treats a nonexistent
# path argument as a hard usage error rather than an empty suite.
test:
	cd backend && $(VENV_BIN)pytest $$(ls -d tests/unit tests/integration tests/regression 2>/dev/null) -q

test-unit:
	cd backend && $(VENV_BIN)pytest tests/unit -q

test-regression:
	cd backend && $(VENV_BIN)pytest tests/regression -q

test-live:
	cd backend && $(VENV_BIN)pytest tests/contract -m live -v

# Keberadaan folder frontend bukan penanda yang benar: npx jatuh ke tsc milik sistem
# kalau node_modules belum ada, dan pesan errornya tidak menyebut dependency sama sekali.
# Lewatnya diumumkan, tidak didiamkan, supaya skip tidak terbaca sebagai lolos.
SKIP_FE = echo "frontend dilewati: jalankan 'cd frontend && npm install' lebih dulu"

test-fe:
	@if [ -d frontend/node_modules ]; then cd frontend && npm run test; else $(SKIP_FE); fi

test-e2e:
	@if [ -d frontend/node_modules ]; then cd frontend && npx playwright test; else $(SKIP_FE); fi

check:
	cd backend && $(VENV_BIN)ruff check . && $(VENV_BIN)ruff format --check . && $(VENV_BIN)mypy app
	@if [ -d frontend/node_modules ]; then cd frontend && npx tsc --noEmit && npm run lint; else $(SKIP_FE); fi
	$(MAKE) test
	$(MAKE) test-fe

demo:
	SCORING_ENGINE=mock $(MAKE) up
