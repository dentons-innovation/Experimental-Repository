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
| **Dependency Review**  | `.github/workflows/dependency-review.yml` | `Dependency Review`      | Recommended (Next)  | :white_check_mark: Active   |
| **Container Security** | `.github/workflows/security-trivy.yml` | `Docker Build & Trivy Scan` |         No          | :warning: Experimental      |
| **OpenSSF Scorecard**  | `.github/workflows/scorecard.yml`      | `Scorecard Analysis`        |         No          | :shield: Advisory           |

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

### Dependency Review (`.github/workflows/dependency-review.yml`)

The Dependency Review workflow provides proactive supply-chain gating on pull requests targeting `main`:

- **PR-Scoped Validation**: Runs GitHub's official `actions/dependency-review-action@v4` on pull request events.
- **Vulnerability Blocking**: Configured with `fail-on-severity: high`, failing the check if a PR introduces direct or transitive dependencies containing known `HIGH` or `CRITICAL` vulnerabilities.
- **Complements Dependabot**:
  - *Dependabot* operates out-of-band on a schedule to detect and update existing dependencies across the repo.
  - *Dependency Review* acts as an in-band PR gate to prevent new vulnerable packages or vulnerable transitive upgrades from entering `main`.
- **Ruleset Recommendation**: Recommended to run as an active check and become a mandatory required status check in the GitHub ruleset after successful validation across initial PRs.

### Container Security Scan (`.github/workflows/security-trivy.yml`)

The container security workflow performs:

- **Docker Build Validation**: Builds the backend Docker image.
- **Trivy Vulnerability Scan**: Scans the resulting image for known operating-system and library vulnerabilities.
- **Severity Threshold**: Reports and fails on configured `HIGH` and `CRITICAL` vulnerabilities.

> [!WARNING]
> This workflow is currently **experimental** and is not configured as a required merge check while container packaging is still being refined.

### OpenSSF Scorecard (`.github/workflows/scorecard.yml`)

The OpenSSF Scorecard workflow provides automated supply-chain security and repository hygiene evaluation:

- **Official Reference Pattern**: Implements the official OpenSSF `ossf/scorecard-action@v2.4.4` reference workflow.
- **Cadence & Execution**: Executes on pushes to `main` and on a weekly Monday schedule (`cron: '0 4 * * 1'`), as well as manual trigger (`workflow_dispatch`).
- **Transparency & SARIF Integration**: Authenticates via GitHub OIDC (`id-token: write`) to publish scores (`publish_results: true`) and uploads findings as SARIF reports to GitHub Code Scanning (`github/codeql-action/upload-sarif@v3`).
- **Hygiene Checks Evaluated**: Evaluates token permissions, dangerous workflow constructs, branch protection rulesets, dependency update tools, and pinned dependencies.
- **Advisory Policy**: Scorecard runs strictly as an **advisory** audit tool and is never configured as a blocking merge check.

### CI Optimization, Caching & Concurrency Architecture

To minimize GitHub Actions execution duration and eliminate wasted runner minutes without weakening security controls, all workflows implement the following engineering practices:

1. **Workflow Concurrency (`cancel-in-progress: true`)**:
   - Each workflow defines `concurrency: group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true`.
   - When a developer pushes a new commit to an active PR branch, any existing in-flight run for that branch is immediately terminated, freeing runner capacity and eliminating duplicate runs.

2. **Deterministic Package Caching**:
   - **Frontend**: Cached via `actions/setup-node@v4` with `cache: 'npm'` keyed to `./frontend/package-lock.json`. This caches the global npm package download store (`~/.npm`) while executing a strict `npm ci` install every run.
   - **Backend**: Cached via `actions/setup-python@v5` with `cache: 'pip'` keyed to both `./backend/requirements.txt` and `./backend/requirements-dev.txt`. This caches pip wheels in `~/.cache/pip` while creating a fresh virtual environment per run.
   - **Security Guarantee**: `node_modules` and Python virtual environments (`.venv`) are **never cached directly**. Direct filesystem caching of executable directories across PRs risks cache poisoning and nondeterministic builds.

3. **Least-Privilege Permissions**:
   - Workflows explicitly declare minimal permissions (`permissions: contents: read` by default). Elevated permissions (`security-events: write`, `id-token: write`) are strictly restricted to the specific Scorecard job requiring SARIF upload and OIDC exchange.

4. **Preservation of Required Check Names & Avoidance of Path Filtering**:
   - The job names `Lint, Test, and Build` and `Lint, Typecheck, and Test` are preserved verbatim to maintain branch protection continuity.
   - Aggressive path filtering (`paths: ['backend/**']`) is intentionally omitted from required checks to prevent checks from entering permanent pending or missing states on cross-cutting or documentation-only pull requests.

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

| Check Name                  | Source Workflow          | Policy                              | Description |
| :-------------------------- | :----------------------- | :---------------------------------- | :---------- |
| `Lint, Test, and Build`     | Frontend CI              | **Required** :white_check_mark:     | Formats, lints, type-checks, tests (Vitest), and builds frontend. |
| `Lint, Typecheck, and Test` | Backend CI               | **Required** :white_check_mark:     | Formats, lints, type-checks (Mypy), migrates, and tests (85% cov). |
| `Dependency Review`         | Dependency Review        | Advisory :warning: *(Recommend Required)* | Blocks PRs introducing dependencies with HIGH/CRITICAL vulnerabilities. |
| `CodeQL`                    | GitHub Advanced Security | **Required** _(enable once stable)_ | Semantic data-flow and static application security analysis. |
| `Docker Build & Trivy Scan` | Container Security       | Advisory _(experimental)_           | Scans container packaging for base image & package CVEs. |
| `Scorecard Analysis`        | OpenSSF Scorecard        | Advisory _(supply-chain audit)_     | Automated repository supply chain hygiene and security scorecard. |
| `Greptile Review`           | Greptile AI              | Advisory                            | Architectural, cross-file, and contract review. |

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
│  • Frontend Build & Test  │ │   • Dependency Review    │
│  • Backend Test & Type    │ │   • Trivy Container Scan │
│                           │ │   • Greptile AI Review   │
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
│    (Triggers OpenSSF Scorecard & Trivy on main)        │
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
