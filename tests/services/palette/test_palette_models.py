"""Behaviour of a palette entry, in particular that it cannot be half-usable."""

from __future__ import annotations

from sysbar.services.palette.models import (
    EntryKind,
    PaletteEntry,
    Runnable,
    Unavailable,
)


def _runnable(calls: list[str]) -> PaletteEntry:
    return PaletteEntry(
        id="open-panel",
        title="Open the panel",
        kind=EntryKind.COMMAND,
        activation=Runnable(invoke=lambda: calls.append("ran")),
    )


def _unavailable() -> PaletteEntry:
    return PaletteEntry(
        id="toggle-microphone",
        title="Mute the microphone",
        kind=EntryKind.TOGGLE,
        activation=Unavailable(reason="No microphone available"),
    )


def test_a_runnable_entry_reports_itself_runnable() -> None:
    assert _runnable([]).is_runnable is True


def test_an_unavailable_entry_does_not() -> None:
    assert _unavailable().is_runnable is False


def test_activating_a_runnable_entry_invokes_it() -> None:
    calls: list[str] = []

    assert _runnable(calls).activate() is True
    assert calls == ["ran"]


def test_activating_an_unavailable_entry_does_nothing() -> None:
    assert _unavailable().activate() is False


def test_an_unavailable_entry_carries_its_reason() -> None:
    assert _unavailable().unavailable_reason == "No microphone available"


def test_a_runnable_entry_has_no_reason_to_give() -> None:
    assert _runnable([]).unavailable_reason == ""


def test_the_haystack_defaults_to_the_title() -> None:
    assert _runnable([]).haystack == "Open the panel"


def test_the_haystack_uses_the_search_text_when_set() -> None:
    entry = PaletteEntry(
        id="clip",
        title="ghp_••••",
        kind=EntryKind.CLIPBOARD,
        activation=Unavailable(reason="x"),
        search_text="ghp_realvalue",
    )

    assert entry.haystack == "ghp_realvalue"


def test_an_entry_is_not_masked_by_default() -> None:
    assert _runnable([]).masked is False
