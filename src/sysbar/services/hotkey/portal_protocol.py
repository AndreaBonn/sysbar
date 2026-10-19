"""Portal request paths and session decisions, independent of D-Bus transport."""

from __future__ import annotations

from collections.abc import Mapping

PORTAL_PATH = "/org/freedesktop/portal/desktop"
_RESPONSE_SUCCESS = 0


def request_path(unique_name: str, handle_token: str) -> str:
    """The Request object path for a call made with ``handle_token``.

    The portal spec makes it deterministic from our unique bus name and the
    token, so a caller can subscribe to its Response before the call returns
    and never miss a fast reply.
    """
    unique = unique_name.lstrip(":").replace(".", "_")
    return f"{PORTAL_PATH}/request/{unique}/{handle_token}"


def session_handle_from(response_code: int, results: Mapping[str, str]) -> str | None:
    """Return the session handle only when the portal accepted the request."""
    if response_code != _RESPONSE_SUCCESS:
        return None
    return results.get("session_handle")
