# Repository Architecture & Governance Rules

- **Security & Secrets**: Never commit hardcoded API keys, database credentials, secrets, or auth tokens. Avoid logging sensitive data, credentials, or PII.
- **Architectural Boundaries**: Maintain strict isolation between `frontend` and `backend`. Do not introduce cross-boundary direct dependencies or implicit couplings.
- **PR Scope & Cleanliness**: Keep pull requests focused on a single responsibility. Avoid mixing unrelated domain changes or infrastructure refactors into feature PRs.
- **Test Integrity**: Ensure new domain features and bug fixes include relevant tests. Do not approve PRs that remove or bypass existing unit or integration tests.
- **Linter Deference**: Defer formatting and stylistic enforcement to Ruff (backend) and ESLint/Prettier (frontend); focus reviews on architecture, logic, and security.
