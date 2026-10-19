import pytest

from sysbar.app.clipboard_content import empty_state, pin_presentation


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("x", ("No entries match", "Try fewer letters.")),
        (
            "",
            (
                "Nothing copied yet",
                "Copy some text or a link anywhere: it appears here, ready to copy again.",
            ),
        ),
    ],
)
def test_empty_state_query_returns_exact_text(query: str, expected: tuple[str, str]) -> None:
    assert empty_state(query=query) == expected


@pytest.mark.parametrize(
    ("pinned", "expected"),
    [
        (True, ("starred-symbolic", "Unpin")),
        (False, ("non-starred-symbolic", "Pin")),
    ],
)
def test_pin_presentation_pinned_returns_icon_and_tooltip(
    pinned: bool,
    expected: tuple[str, str],
) -> None:
    assert pin_presentation(pinned=pinned) == expected
