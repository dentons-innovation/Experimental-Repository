# Repository Governance & CI/CD Pipeline

This document outlines the automated checks, code review guidelines, and security policies governing the ProjectFlow repository.

---

## 1. Continuous Integration (GitHub Actions)

Our CI pipeline guarantees that the `main` branch remains green and production-ready. Workflows run on every pull request and push to `main` without path filters, ensuring that required status checks never get stuck in a pending state on partial changes.

### Frontend CI (`.github/workflows/ci-frontend.yml`)
- **Format Check**: Verifies formatting against Prettier (`npm run format:check`).
- **Linting**: Enforces JavaScript/TypeScript linting with ESLint (`npm run lint`).
- **Type Checking**: Validates TypeScript types across the codebase with `tsc` (`npm run typecheck`).
- **Testing & Coverage**: Runs Vitest test suite and collects coverage (`npm run test:coverage`).
- **Production Build**: Validates that the Vite bundle compiles cleanly (`npm run build`).

### Backend CI (`.github/workflows/ci-backend.yml`)
- **Format & Lint**: Runs Ruff formatting checks and linter (`ruff format --check .`, `ruff check .`).
- **Static Type Check**: Runs `mypy app` for strict Python type checking.
- **Application Startup Validation**: Runs `python -c "import app.main; print('App loaded successfully')"` to verify module imports and initialization.
- **Database Migrations**: Runs `alembic upgrade head` against a live PostgreSQL service container to verify schema validity.
- **Testing & Coverage**: Executes pytest unit and integration suites against the PostgreSQL test database with minimum coverage enforcement (`pytest tests/unit tests/api -v --cov=app --cov-fail-under=85`).

### Container Security Scan (`.github/workflows/security-trivy.yml`)
- **Docker Build**: Validates building the backend Docker image.
- **Trivy Vulnerability Scan**: Scans the built image for OS and library vulnerabilities (`HIGH,CRITICAL`).
- **Status**: **Experimental**. This workflow runs on PRs to provide visibility into container dependencies, but is **not** recommended as a blocking required check yet while container packaging is being refined.

> **Note on CodeQL**: CodeQL static analysis is managed and configured separately and is excluded from this baseline workflow set.

---

## 2. AI Code Reviews (Greptile)

We utilize **Greptile** for context-aware code reviews targeting domain architecture, security invariants, and boundaries that static linters (Ruff / ESLint) do not cover.

Greptile uses a **directory-scoped** configuration model:

```
.
├── .greptile/
│   ├── config.json          # Repository-level Greptile configuration
│   └── rules.md             # Repository-wide governance, security, and PR discipline
├── backend/
│   └── .greptile/
│       └── rules.md         # FastAPI, service layer, repository pattern & authorization rules
└── frontend/
    └── .greptile/
        └── rules.md         # React Query, type safety, custom hook boundaries & UI rules
```

- **`.greptile/rules.md` (Root)**: Enforces secrets protection, clean separation between frontend and backend, single-responsibility PRs, and deference to linters for formatting.
- **`backend/.greptile/rules.md`**: Enforces thin route handlers (`app/api/`), service orchestration (`app/services/`), isolated database access (`app/repositories/`), authorization checks (`authorization.py`), and mandatory Alembic migrations for model changes.
- **`frontend/.greptile/rules.md`**: Enforces TanStack Query for server state, centralized query keys, strict TypeScript typing (no unchecked `any`), and component simplicity.

---

## 3. Dependency Management (Dependabot)

`.github/dependabot.yml` is configured to periodically monitor dependencies:
- **npm** (frontend): Weekly updates.
- **pip** (backend): Weekly updates.
- **Docker**: Weekly updates for base image tags.
- **GitHub Actions**: Weekly updates for CI action versions.

---

## 4. GitHub Rulesets Configuration (Recommended)

GitHub has replaced legacy branch protection with **Rulesets** (available in **Repository Settings → Rules → Rulesets**). To enforce branch protection on `main`, configure a ruleset using the steps below:

### Step-by-Step Setup:

1. In your GitHub repository, navigate to **Settings**.
2. In the left sidebar under **Code and automation**, click **Rules** → **Rulesets**.
3. Click the green **New ruleset** button and select **New branch ruleset**.
4. Configure the ruleset:
   - **Ruleset Name**: Enter a name, such as `main-protection`.
   - **Enforcement status**: Set to **Active** (or **Evaluate** to preview without blocking).
5. **Target branches**:
   - Click **Add target** → select **Include default branch** (or **Include by pattern** and enter `main`).
6. **Branch Rules**:
   - Check **Restrict deletions**.
   - Check **Block force pushes**.
   - Check **Require a pull request before merging**:
     - *Required approvals*: Set to **1** (only 1 approval required for now).
     - *Dismiss stale pull request approvals when new commits are pushed*: Checked.
     - *Require review from Code Owners*: Optional, if `CODEOWNERS` is used.
   - Check **Require status checks to pass**:
     - Click **Add checks** and search for the following two jobs:
       1. `Lint, Test, and Build` (Frontend CI)
       2. `Lint, Typecheck, and Test` (Backend CI)
     - Check **Require branches to be up to date before merging** to guarantee checks run against the latest commit.
     - ⚠️ **Important**: Do **NOT** add `Docker Build & Trivy Scan` as a required status check at this stage. Container scanning is currently experimental.
     - *(Optional)* Add Greptile status checks if Greptile PR gating is enabled for your organization.
7. Click **Create** (or **Save changes**).
