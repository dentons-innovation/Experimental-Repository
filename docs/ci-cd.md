# Repository Governance & CI/CD Pipeline

This document outlines the automated checks, code review guidelines, security controls, and repository rules governing the ProjectFlow repository.

---

## 1. Continuous Integration

GitHub Actions workflows run on every pull request targeting `main` and on every push to `main`. The CI pipeline is responsible for deterministic validation before code is merged.

### Overview of Workflows

| Workflow               | Configuration File                     | Jobs / Status Checks        | Required in Ruleset | Status                      |
| :--------------------- | :------------------------------------- | :-------------------------- | :-----------------: | :-------------------------- |
| **Frontend CI**        | `.github/workflows/ci-frontend.yml`    | `Lint, Test, and Build`     |         Yes         | :white_check_mark: Enforced |
| **Backend CI**         | `.github/workflows/ci-backend.yml`     | `Lint, Typecheck, and Test` |         Yes         | :white_check_mark: Enforced |
| **Container Security** | `.github/workflows/security-trivy.yml` | `Docker Build & Trivy Scan` |         No          | :warning: Experimental      |

### Frontend CI (`.github/workflows/ci-frontend.yml`)

The frontend workflow performs:

- **Format Check**: Validates formatting with Prettier using `npm run format:check`.
- **Linting**: Runs ESLint using `npm run lint`.
- **Type Checking**: Validates TypeScript types across the codebase using `npm run typecheck`.
- **Testing and Coverage**: Runs the Vitest test suite with coverage collection using `npm run test:coverage`.
- **Production Build**: Verifies that the Vite production bundle builds successfully using `npm run build`.

> **Purpose**: Prevents formatting issues, lint violations, type errors, test regressions, insufficient coverage, and broken frontend builds from reaching `main`.

### Backend CI (`.github/workflows/ci-backend.yml`)

The backend workflow performs:

- **Format Check**: Runs Ruff formatting checks with `ruff format --check .`.
- **Linting**: Runs Ruff linter with `ruff check .`.
- **Static Type Checking**: Runs `mypy app` for strict Python type checking.
- **Application Import Validation**: Imports the FastAPI application using `python -c "import app.main"` to catch initialization and import failures.
- **PostgreSQL Service Setup**: Boots a live PostgreSQL service container for database-backed integration tests.
- **Database Migration Validation**: Executes `alembic upgrade head` against PostgreSQL to verify schema validity.
- **Testing and Coverage**: Executes pytest unit and integration suites against PostgreSQL and enforces the configured minimum coverage threshold (`--cov-fail-under=85`).

> **Purpose**: Detects Python quality issues, type errors, application initialization failures, invalid database migrations, integration regressions, and test failures before merge.

### Container Security Scan (`.github/workflows/security-trivy.yml`)

The container security workflow performs:

- **Docker Build Validation**: Builds the backend Docker image.
- **Trivy Vulnerability Scan**: Scans the resulting image for known operating-system and library vulnerabilities.
- **Severity Threshold**: Reports and fails on configured `HIGH` and `CRITICAL` vulnerabilities.

> [!WARNING]
> This workflow is currently **experimental** and is not configured as a required merge check while container packaging is still being refined.

### CodeQL

GitHub CodeQL is configured separately from the repository workflow files. CodeQL provides static application security testing (SAST) by analyzing source-code structure and data flow for security-relevant patterns that are not normally detected by linters or unit tests.

Once CodeQL analysis is active and stable, its results can be enforced as a required status check through the repository ruleset.

---

## 2. AI Code Review (Greptile)

We utilize **Greptile** for repository-aware pull request reviews. Greptile complements deterministic CI by reviewing areas such as architectural consistency, authorization, data-access boundaries, cross-file regressions, and framework-specific conventions.

It is intentionally not used for concerns already enforced by deterministic tools such as Ruff, ESLint, Prettier, or TypeScript.

### Greptile Configuration Model

Greptile uses directory-scoped configuration:

```text
.
├── .greptile/
│   ├── config.json          # Repository-level configuration
│   └── rules.md             # Global governance, security, and PR discipline
├── backend/
│   └── .greptile/
│       └── rules.md         # FastAPI, service layer, repository pattern & authorization
└── frontend/
    └── .greptile/
        └── rules.md         # React Query, type safety, custom hook boundaries & UI rules
```

### Scoped Rule Sets

#### Root Rules (`.greptile/rules.md`)

- **No hardcoded secrets**: Never commit credentials, tokens, or private keys.
- **Clear frontend/backend separation**: Enforce strict boundary isolation between tiers.
- **Focused pull requests**: Keep PRs scoped to a single logical responsibility.
- **Preservation of architectural boundaries**: Guard against layering violations.
- **Test integrity**: Maintain unit/integration test coverage for all modified features.
- **Avoid duplicate style feedback**: Defer formatting and syntax enforcement to Ruff, ESLint, and Prettier.

#### Backend Rules (`backend/.greptile/rules.md`)

- **Thin route handlers**: Keep API routes minimal; delegate business logic to services.
- **Service layer orchestration**: Centralize domain operations and business validation in services.
- **Repository data access**: Isolate database queries and ORM interactions to repositories.
- **Explicit authorization**: Verify user permissions on all protected resources.
- **Transaction handling**: Ensure atomic commits and proper rollback semantics.
- **Alembic migrations**: Require migration scripts for all database model alterations.
- **Contract preservation**: Protect existing API contracts and response schemas against unintentional breaks.

#### Frontend Rules (`frontend/.greptile/rules.md`)

- **TanStack Query for server state**: Manage all remote data caching and synchronization through React Query.
- **Centralized query keys**: Organize query keys in central factories to prevent cache collisions.
- **Typed API access**: Wrap all backend endpoints in strongly typed fetcher functions.
- **Strict TypeScript**: Disallow unchecked `any` and enforce complete entity interfaces.
- **Custom hooks**: Encapsulate reusable stateful logic into dedicated custom hooks.
- **Component boundaries**: Maintain modular, focused components without redundant complexity.

> [!NOTE]
> Greptile is initially advisory and is not configured as a mandatory blocking merge gate.

---

## 3. Dependency Management (Dependabot)

Dependabot is configured in `.github/dependabot.yml` and periodically monitors dependencies across all active package ecosystems:

| Ecosystem          | Directory   | Schedule | Target Scope                            |
| :----------------- | :---------- | :------- | :-------------------------------------- |
| **npm**            | `/frontend` | Weekly   | Frontend dependencies & devDependencies |
| **pip**            | `/backend`  | Weekly   | Python backend dependencies             |
| **Docker**         | `/backend`  | Weekly   | Container base image tags               |
| **GitHub Actions** | `/`         | Weekly   | CI/CD workflow action versions          |

- Routine dependency version updates run on the configured weekly schedule.
- Dependabot security alerts and automated security pull requests trigger immediately when GitHub identifies vulnerable dependencies.

---

## 4. Secret Protection

GitHub Secret Scanning and Push Protection are active for this repository:

- **Proactive Detection**: Detects supported credentials, private keys, database connection strings, and tokens before they are accepted by the remote.
- **Zero Secrets in Code**: Secrets must never be stored in source control. Runtime configuration and credentials must always be supplied through environment variables or GitHub Actions repository secrets.

> [!IMPORTANT]
> If a credential is accidentally committed, treat it as compromised immediately: revoke, rotate, and invalidate the key rather than simply deleting it in a subsequent commit.

---

## 5. Repository Ruleset (Branch Protection)

The `main` branch is protected using a modern GitHub branch ruleset. Configure rulesets under:

```text
Repository Settings → Rules → Rulesets
```

### Recommended Ruleset Configuration

Create a branch ruleset targeting the default branch (`main`):

- **Enforcement Status**: `Active` (or `Evaluate` to dry-run without blocking)
- **Target Branches**: `default branch / main`
- **Restrict Deletions**: Enabled
- **Block Force Pushes**: Enabled
- **Require a Pull Request Before Merging**: Enabled
  - _Required approvals_: `1` (optional for solo development; set to 1+ for multi-contributor repositories)
  - _Dismiss stale approvals when new commits are pushed_: Enabled
  - _Require review from Code Owners_: Optional (if `CODEOWNERS` is maintained)
- **Require Status Checks to Pass Before Merging**: Enabled
  - _Require branches to be up to date before merging_: Enabled
  - _Require conversations to be resolved before merging_: Enabled

### Required vs. Advisory Checks

| Check Name                  | Source Workflow          | Policy                              |
| :-------------------------- | :----------------------- | :---------------------------------- |
| `Lint, Test, and Build`     | Frontend CI              | **Required** :white_check_mark:     |
| `Lint, Typecheck, and Test` | Backend CI               | **Required** :white_check_mark:     |
| `CodeQL`                    | GitHub Advanced Security | **Required** _(enable once stable)_ |
| `Docker Build & Trivy Scan` | Container Security       | Advisory _(experimental)_           |
| `Greptile Review`           | Greptile AI              | Advisory                            |

---

## 6. Pull Request Workflow

### End-to-End Promotion Flow

```text
┌────────────────────────────────────────────────────────┐
│                     Feature Branch                     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                  Open Pull Request                     │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌───────────────────────────┐ ┌──────────────────────────┐
│  Deterministic CI Checks  │ │   Security & AI Review   │
│  • Frontend Build & Test  │ │   • Trivy Container Scan │
│  • Backend Test & Type    │ │   • Greptile AI Review   │
└─────────────┬─────────────┘ └───────────┬──────────────┘
              │                           │
              └─────────────┬─────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│              All Required Checks Pass                  │
│       • Frontend CI  ✔    • Backend CI  ✔              │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             Branch Ruleset Allows Merge                │
│       • Approvals Met     • Up-to-Date with main       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                      Merged to main                    │
└────────────────────────────────────────────────────────┘
```

### The Four Categories of Pipeline Control

The governance model cleanly separates four distinct categories of verification:

#### 1. Deterministic Validation

_Handled by GitHub Actions on every pull request and push:_

- **Formatting**: Prettier (frontend) and Ruff (backend)
- **Linting**: ESLint (TypeScript/React) and Ruff (Python)
- **Type Checking**: Strict `tsc` compiler checks and `mypy app`
- **Testing**: Automated Vitest unit tests and pytest unit/integration suites
- **Coverage**: Enforced coverage thresholds on test suites
- **Production Builds**: Full Vite bundle compilation validation
- **Database Migrations**: Automated PostgreSQL `alembic upgrade head` verification
- **Application Startup**: Zero-downtime startup smoke tests (`python -c "import app.main"`)

#### 2. Security Validation

_Handled by automated security scanners and dependency monitors:_

- **CodeQL**: Deep static data flow, taint analysis, and vulnerability detection
- **Dependabot**: Continuous vulnerability monitoring and automated security updates
- **Secret Scanning & Push Protection**: Pre-commit and post-commit credential leak blocking
- **Trivy**: Container image scanning for OS, CVE, and library package vulnerabilities

#### 3. Contextual Review

_Handled by AI and human reviewers:_

- **Greptile**: Architecture conformance, API contract safety, cross-file impact analysis
- **Human Review**: Domain intent, product fit, user experience, and manual sign-off

#### 4. Repository Governance

_Handled by GitHub Rulesets:_

- **Branch Protection**: Prevention of direct pushes, force pushes, and branch deletions on `main`
- **Merge Restrictions**: Gating merges behind green status checks and required approvals
- **Linear Progression**: Ensuring branches are synchronized and conversations resolved before merging
