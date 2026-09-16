"""Domain exceptions.

Pure Python exceptions with no framework dependencies.
Service layer raises these; API layer maps them to HTTP responses.

This separation lets us unit-test service logic without an HTTP context.
"""

from __future__ import annotations


class ProjectFlowError(Exception):
    """Base class for all domain errors."""


class AuthenticationError(ProjectFlowError):
    """JWT or credential validation failed."""


class AuthorizationError(ProjectFlowError):
    """The authenticated user lacks permission for this operation."""

    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message)


class NotFoundError(ProjectFlowError):
    """Requested resource does not exist or is not visible to the caller."""

    def __init__(self, resource: str = "Resource", resource_id: str | None = None) -> None:
        msg = f"{resource} not found"
        if resource_id:
            msg = f"{resource} '{resource_id}' not found"
        super().__init__(msg)
        self.resource = resource
        self.resource_id = resource_id


class ConflictError(ProjectFlowError):
    """Resource already exists or unique constraint would be violated."""

    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message)


class ValidationError(ProjectFlowError):
    """Business-rule validation failure (distinct from schema validation)."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class OptimisticLockError(ProjectFlowError):
    """Concurrent update detected — the resource version has changed.

    The client should re-fetch the resource and retry the update.
    This is the application-level optimistic concurrency exception.
    Maps to HTTP 409 Conflict with a specific error code.
    """

    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(
            f"{resource} was modified by another request. "
            "Re-fetch the resource and retry."
        )
        self.resource = resource
