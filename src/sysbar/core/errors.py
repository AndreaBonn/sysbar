"""Exception hierarchy for Sysbar.

Exceptions are caught only at boundaries (UI handlers, CLI, D-Bus callbacks),
never swallowed inside business logic.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all application errors.

    Parameters
    ----------
    message
        Human-readable description, safe to surface to the user.
    code
        Stable machine-readable error code.
    """

    code = "INTERNAL_ERROR"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class ValidationError(AppError):
    """Raised when input fails validation at a boundary."""

    code = "VALIDATION_ERROR"


class NotFoundError(AppError):
    """Raised when a requested entity does not exist."""

    code = "NOT_FOUND"

    def __init__(self, entity: str, identifier: str) -> None:
        super().__init__(f"{entity} {identifier} not found")


class CapabilityError(AppError):
    """Raised when a feature is invoked but its capability is unavailable."""

    code = "CAPABILITY_UNAVAILABLE"

    def __init__(self, capability: str) -> None:
        super().__init__(f"capability '{capability}' is not available")
        self.capability = capability


class PrivilegedActionError(AppError):
    """Raised when a privileged (pkexec) action fails or is denied."""

    code = "PRIVILEGED_ACTION_FAILED"
