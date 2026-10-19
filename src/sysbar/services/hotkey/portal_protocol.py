"""Portal request paths and session decisions, independent of D-Bus transport."""

from __future__ import annotations

from collections.abc import Mapping

PORTAL_PATH = "/org/freedesktop/portal/desktop"
_RESPONSE_SUCCESS = 0


def request_path(unique_name: str, handle_token: str) -> str:
    """Derive the Request path so callers can subscribe before CreateSession."""
    unique = unique_name.lstrip(":").replace(".", "_")
    return f"{PORTAL_PATH}/request/{unique}/{handle_token}"


def session_handle_from(response_code: int, results: Mapping[str, str]) -> str | None:
    """Return the session handle only when the portal accepted the request."""
    if response_code != _RESPONSE_SUCCESS:
        return None
    return results.get("session_handle")
