"""Portal protocol decisions without a running desktop portal."""

from __future__ import annotations

import pytest

from sysbar.services.hotkey.portal_protocol import request_path, session_handle_from


def test_request_path_normalizes_unique_bus_name() -> None:
    assert request_path(unique_name=":1.42", handle_token="sysbar_shortcuts") == (
        "/org/freedesktop/portal/desktop/request/1_42/sysbar_shortcuts"
    )


@pytest.mark.parametrize(
    ("response_code", "results", "expected"),
    [
        (0, {"session_handle": "/session/42"}, "/session/42"),
        (1, {"session_handle": "/session/42"}, None),
        (0, {}, None),
    ],
)
def test_session_handle_from_response(
    response_code: int,
    results: dict[str, str],
    expected: str | None,
) -> None:
    assert session_handle_from(response_code=response_code, results=results) == expected
