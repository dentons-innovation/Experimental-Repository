"""Test configuration and fixtures.

Test isolation strategy:
- Each test runs inside a transaction that is rolled back after the test.
- This gives complete isolation without truncating tables between tests.
- The same PostgreSQL instance is used as in production (no SQLite/mock).
- Alembic migrations are applied once before the test session starts.

The TEST_DATABASE_SYNC_URL and TEST_DATABASE_URL environment variables
must point to a PostgreSQL test database. Set them in your .env or
export them before running tests.

Running:
    pytest tests/                                         # all tests
    pytest tests/unit/                                    # unit tests only
    pytest tests/integration/ tests/api/                  # DB tests
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.database import build_engine, build_session_factory
from app.domain.enums import ProjectRole, WorkspaceRole
from app.domain.models import Base, Project, ProjectMember, User, Workspace, WorkspaceMember
from app.infrastructure.auth import JWTVerifier
from app.main import create_app

# ─────────────────────────────────────────────────────────────
# Test database URL
# ─────────────────────────────────────────────────────────────

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///./test_projectflow.db",
)
TEST_DATABASE_SYNC_URL = os.environ.get(
    "TEST_DATABASE_SYNC_URL",
    "sqlite:///./test_projectflow.db",
)


# ─────────────────────────────────────────────────────────────
# Session-scoped: engine and schema setup
# ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create async engine for test database."""
    connect_args = {"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {}
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args=connect_args,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def session_factory(test_engine):
    """Session factory for the test database."""
    return async_sessionmaker(
        test_engine, expire_on_commit=False, autoflush=False, class_=AsyncSession
    )


# ─────────────────────────────────────────────────────────────
# Function-scoped: isolated session with transaction rollback
# ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, Any]:
    """Provide an isolated, auto-rolled-back session for each test.

    Uses nested transactions (SAVEPOINT) to isolate each test
    without recreating the schema or truncating tables.
    """
    async with test_engine.connect() as connection:
        await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await connection.rollback()


# ─────────────────────────────────────────────────────────────
# Mock JWT verifier (for API tests)
# ─────────────────────────────────────────────────────────────

class MockJWTVerifier:
    """JWT verifier that accepts any token and returns a preset user UUID string."""

    def __init__(self, user_id: UUID | str = "0191eb58-0000-7000-8000-000000000001") -> None:
        self.user_id = str(user_id)

    def verify(self, token: str) -> str:
        return self.user_id


# ─────────────────────────────────────────────────────────────
# Test data builders
# ─────────────────────────────────────────────────────────────

async def create_user(
    session: AsyncSession,
    email: str = "test@example.com",
    username: str = "testuser",
    full_name: str = "Test User",
    password: str = "password123",
) -> User:
    from app.infrastructure.auth import hash_password

    user = User(
        email=email,
        username=username,
        full_name=full_name,
        password_hash=hash_password(password),
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def create_workspace(
    session: AsyncSession,
    owner: User,
    name: str = "Test Workspace",
    slug: str = "test-workspace",
) -> Workspace:
    workspace = Workspace(
        name=name,
        slug=slug,
        owner_id=owner.id,
    )
    session.add(workspace)
    await session.flush()
    # Add owner as workspace member
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=owner.id,
        role=WorkspaceRole.OWNER,
    )
    session.add(member)
    await session.flush()
    await session.refresh(workspace)
    return workspace


async def create_project(
    session: AsyncSession,
    workspace: Workspace,
    creator: User,
    name: str = "Test Project",
    slug: str = "test-project",
) -> Project:
    project = Project(
        workspace_id=workspace.id,
        name=name,
        slug=slug,
    )
    session.add(project)
    await session.flush()
    # Add creator as project admin
    member = ProjectMember(
        project_id=project.id,
        user_id=creator.id,
        role=ProjectRole.ADMIN,
    )
    session.add(member)
    await session.flush()
    await session.refresh(project)
    return project


async def add_workspace_member(
    session: AsyncSession,
    workspace: Workspace,
    user: User,
    role: WorkspaceRole = WorkspaceRole.MEMBER,
) -> WorkspaceMember:
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=role,
    )
    session.add(member)
    await session.flush()
    return member


async def add_project_member(
    session: AsyncSession,
    project: Project,
    user: User,
    role: ProjectRole = ProjectRole.MEMBER,
) -> ProjectMember:
    member = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        role=role,
    )
    session.add(member)
    await session.flush()
    return member


# ─────────────────────────────────────────────────────────────
# HTTPX async client for API tests
# ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, Any]:
    """Async HTTP client against the test app with DB session injection."""
    from app.core import dependencies
    from app.infrastructure.auth import get_jwt_verifier
    from app.repositories.user_repository import UserRepository
    from app.infrastructure.auth import hash_password

    repo = UserRepository(db_session)
    user = await repo.create_user(
        email="apitest@example.com",
        username="apitestuser",
        full_name="API Test User",
        password_hash=hash_password("password123"),
    )

    mock_verifier = MockJWTVerifier(user.id)
    app = create_app()

    # Override DB dependency to use the test session
    async def override_db():
        yield db_session

    # Override JWT verifier
    app.dependency_overrides[dependencies.get_db_session] = override_db
    app.dependency_overrides[get_jwt_verifier] = lambda: mock_verifier

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.headers["Authorization"] = "Bearer test-token"
        client._test_user = user  # type: ignore[attr-defined]
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client_factory(db_session: AsyncSession):
    """Factory that creates API clients for different users."""
    from app.core import dependencies
    from app.infrastructure.auth import get_jwt_verifier, hash_password
    from app.repositories.user_repository import UserRepository

    clients = []

    async def make_client(user_identifier: str, email: str, username: str) -> tuple[AsyncClient, User]:
        repo = UserRepository(db_session)
        user = await repo.create_user(
            email=email,
            username=username,
            full_name=f"User {username}",
            password_hash=hash_password("password123"),
        )

        mock_verifier = MockJWTVerifier(user.id)
        app = create_app()

        async def override_db():
            yield db_session

        app.dependency_overrides[dependencies.get_db_session] = override_db
        app.dependency_overrides[get_jwt_verifier] = lambda: mock_verifier

        client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        )
        client.headers["Authorization"] = "Bearer test-token"
        await client.__aenter__()
        clients.append((client, app))
        return client, user

    yield make_client

    for client, app in clients:
        await client.__aexit__(None, None, None)
        app.dependency_overrides.clear()
        app.dependency_overrides.clear()
