# ProjectFlow — Unified Developer Commands
# All commands that CI will call are available here.
# Run `make help` to list all targets.

.PHONY: help install install-backend install-frontend \
        lint lint-backend lint-frontend \
        format format-backend format-frontend \
        format-check format-check-backend format-check-frontend \
        typecheck typecheck-backend typecheck-frontend \
        test test-unit test-int test-backend-cov test-frontend test-e2e \
        migrate migrate-rollback migrate-create \
        seed \
        docker-up docker-down docker-logs \
        build build-frontend \
        clean

# ─────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}'

# ─────────────────────────────────────────────────────────────
# Install
# ─────────────────────────────────────────────────────────────
install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend Python dependencies
	cd backend && pip install -r requirements-dev.txt

install-frontend: ## Install frontend Node dependencies
	cd frontend && npm install

# ─────────────────────────────────────────────────────────────
# Lint
# ─────────────────────────────────────────────────────────────
lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Lint backend (ruff)
	cd backend && ruff check .

lint-frontend: ## Lint frontend (eslint)
	cd frontend && npm run lint

# ─────────────────────────────────────────────────────────────
# Format
# ─────────────────────────────────────────────────────────────
format: format-backend format-frontend ## Format all code

format-backend: ## Format backend (ruff format)
	cd backend && ruff format .

format-frontend: ## Format frontend (prettier)
	cd frontend && npm run format

format-check: format-check-backend format-check-frontend ## Check formatting without modifying

format-check-backend: ## Check backend formatting
	cd backend && ruff format --check .

format-check-frontend: ## Check frontend formatting
	cd frontend && npm run format:check

# ─────────────────────────────────────────────────────────────
# Type checking
# ─────────────────────────────────────────────────────────────
typecheck: typecheck-backend typecheck-frontend ## Run all type checks

typecheck-backend: ## Type-check backend (mypy)
	cd backend && mypy app

typecheck-frontend: ## Type-check frontend (tsc)
	cd frontend && npm run typecheck

# ─────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────
test: test-backend-cov test-frontend ## Run backend + frontend tests with coverage

test-unit: ## Run backend unit tests only
	cd backend && pytest tests/unit -v \
		--cov=app --cov-branch --cov-report=term-missing \
		--cov-fail-under=85

test-int: ## Run backend integration + API tests (requires PostgreSQL)
	cd backend && pytest tests/integration tests/api -v \
		--cov=app --cov-branch --cov-report=term-missing

test-backend-cov: ## Run ALL backend tests with coverage enforcement
	cd backend && pytest \
		--cov=app \
		--cov-branch \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=85 \
		-v

test-frontend: ## Run frontend unit/component tests with coverage
	cd frontend && npm run test:coverage

test-e2e: ## Run Playwright E2E tests
	cd frontend && npm run test:e2e

# ─────────────────────────────────────────────────────────────
# Database Migrations
# ─────────────────────────────────────────────────────────────
migrate: ## Apply all pending migrations
	cd backend && alembic upgrade head

migrate-rollback: ## Roll back one migration
	cd backend && alembic downgrade -1

migrate-create: ## Create a new migration (usage: make migrate-create MSG="add_foo")
	cd backend && alembic revision --autogenerate -m "$(MSG)"

migrate-history: ## Show migration history
	cd backend && alembic history --verbose

# ─────────────────────────────────────────────────────────────
# Seed data
# ─────────────────────────────────────────────────────────────
seed: ## Load demo seed data into the database
	cd backend && python scripts/seed.py

# ─────────────────────────────────────────────────────────────
# Docker
# ─────────────────────────────────────────────────────────────
docker-up: ## Start all services
	docker-compose up -d

docker-down: ## Stop all services
	docker-compose down

docker-logs: ## Tail logs from all services
	docker-compose logs -f

docker-test-up: ## Start test database
	docker-compose -f docker-compose.test.yml up -d

docker-test-down: ## Stop test database
	docker-compose -f docker-compose.test.yml down

# ─────────────────────────────────────────────────────────────
# Build
# ─────────────────────────────────────────────────────────────
build: build-frontend ## Build all artifacts

build-frontend: ## Build frontend production bundle
	cd frontend && npm run build

# ─────────────────────────────────────────────────────────────
# Clean
# ─────────────────────────────────────────────────────────────
clean: ## Remove build/cache artifacts
	rm -rf backend/.mypy_cache backend/.ruff_cache backend/htmlcov backend/.coverage
	rm -rf frontend/dist frontend/coverage frontend/playwright-report
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ─────────────────────────────────────────────────────────────
# CI — sequential quality gate (used by GitHub Actions)
# ─────────────────────────────────────────────────────────────
ci: format-check lint typecheck test build ## Full CI quality gate (run locally before pushing)
