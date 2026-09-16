# Backend Architecture Rules (FastAPI)

- **Layering Separation**:
  - Keep route handlers in `app/api/` thin; routers must only handle request validation, dependency injection, and mapping to responses.
  - Encapsulate business logic, domain rules, and transaction orchestration within `app/services/`.
  - Execute all database queries within repository classes (`app/repositories/`). Never inject or execute raw queries/SQLAlchemy sessions directly inside routers.
- **Authorization & Security**:
  - Enforce permission checks (via `app/services/authorization.py`) prior to performing CRUD actions on workspace- or project-scoped entities.
  - Avoid leaking internal database or transaction errors directly to the client; translate to structured HTTP exceptions.
- **Schema & Migrations**:
  - Any changes to database models in `app/domain/models.py` must include a corresponding Alembic migration script under `alembic/versions/`.
- **Linter Deference**:
  - Defer syntax, import sorting, and code style to Ruff; prioritize domain correctness, authorization boundaries, and async database session safety.
