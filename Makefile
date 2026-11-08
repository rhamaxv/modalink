.PHONY: up down migrate test test-unit test-regression test-live test-fe test-e2e check demo

up:
	docker compose up -d db db-test
	cd backend && uvicorn app.main:app --reload

down:
	docker compose down

migrate:
	cd backend && alembic upgrade head

# `ls -d` lists only the test directories that already exist: tests/regression
# and tests/contract arrive in later phases, and pytest treats a nonexistent
# path argument as a hard usage error rather than an empty suite.
test:
	cd backend && pytest $$(ls -d tests/unit tests/integration tests/regression 2>/dev/null) -q

test-unit:
	cd backend && pytest tests/unit -q

test-regression:
	cd backend && pytest tests/regression -q

test-live:
	cd backend && pytest tests/contract -m live -v

# The frontend is scaffolded in phase 10; until then these targets are no-ops
# so `make check` keeps passing on a backend-only tree.
test-fe:
	@if [ -d frontend ]; then cd frontend && npm run test; else echo "frontend not yet scaffolded, skipping until phase 10"; fi

test-e2e:
	@if [ -d frontend ]; then cd frontend && npx playwright test; else echo "frontend not yet scaffolded, skipping until phase 10"; fi

check:
	cd backend && ruff check . && mypy app
	@if [ -d frontend ]; then cd frontend && npx tsc --noEmit && npm run lint; fi
	$(MAKE) test
	$(MAKE) test-fe

demo:
	SCORING_ENGINE=mock $(MAKE) up
