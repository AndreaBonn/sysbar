from __future__ import annotations

import pytest

from sysbar.app.palette_content import (
    RowPresentation,
    RunDecision,
    empty_state,
    row_presentation,
    run_decision,
    section_title,
)
from sysbar.services.palette.models import EntryKind, PaletteEntry, Runnable, Unavailable


def _entry(activation: Runnable | Unavailable, *, masked: bool = False) -> PaletteEntry:
    return PaletteEntry(
        id="test",
        title="Test",
        kind=EntryKind.COMMAND,
        activation=activation,
        subtitle="Original subtitle",
        masked=masked,
    )


def test_run_decision_runnable_returns_run_without_invoking() -> None:
    calls: list[str] = []
    entry = _entry(activation=Runnable(invoke=lambda: calls.append("run")))

    assert run_decision(entry=entry) is RunDecision.RUN
    assert calls == []
    entry.activate()
    assert calls == ["run"]


def test_run_decision_fixable_returns_fix_without_applying() -> None:
    calls: list[str] = []
    entry = _entry(
        activation=Unavailable(
            reason="Disabled",
            fix=lambda: calls.append("fix"),
            fix_label="Enable",
        )
    )

    assert run_decision(entry=entry) is RunDecision.FIX
    assert calls == []
    entry.apply_fix()
    assert calls == ["fix"]


def test_run_decision_unavailable_returns_ignore() -> None:
    entry = _entry(activation=Unavailable(reason="Missing"))
    assert run_decision(entry=entry) is RunDecision.IGNORE


def test_section_title_first_command_returns_actions() -> None:
    assert section_title(kind_value="command", previous_kind_value=None) == "Actions"


def test_section_title_repeated_kind_returns_none() -> None:
    assert section_title(kind_value="command", previous_kind_value=None) == "Actions"
    assert section_title(kind_value="command", previous_kind_value="command") is None


def test_section_title_changed_kind_returns_new_title() -> None:
    assert section_title(kind_value="scene", previous_kind_value="command") == "Scenes"


def test_section_title_unknown_kind_returns_none() -> None:
    assert section_title(kind_value="command", previous_kind_value=None) == "Actions"
    assert section_title(kind_value="unknown", previous_kind_value=None) is None


@pytest.mark.parametrize(
    ("kind", "title"),
    [
        (EntryKind.COMMAND, "Actions"),
        (EntryKind.SCENE, "Scenes"),
        (EntryKind.TOGGLE, "Quick toggles"),
        (EntryKind.CLIPBOARD, "Clipboard"),
        (EntryKind.SHELF, "Shelf"),
        (EntryKind.DEVICE, "Audio devices"),
    ],
)
def test_section_title_each_kind_returns_exact_title(kind: EntryKind, title: str) -> None:
    assert section_title(kind_value=kind.value, previous_kind_value=None) == title


def test_row_presentation_runnable_uses_subtitle_and_is_activatable() -> None:
    entry = _entry(activation=Runnable(invoke=lambda: None))

    assert row_presentation(entry=entry) == RowPresentation(
        subtitle="Original subtitle",
        activatable=True,
        dimmed=False,
        show_reveal=False,
        show_fix=False,
    )


def test_row_presentation_fixable_masked_shows_reason_reveal_and_fix() -> None:
    entry = _entry(
        activation=Unavailable(reason="Disabled", fix=lambda: None, fix_label="Enable"),
        masked=True,
    )

    assert row_presentation(entry=entry) == RowPresentation(
        subtitle="Disabled",
        activatable=False,
        dimmed=False,
        show_reveal=True,
        show_fix=True,
    )


def test_row_presentation_unavailable_without_fix_is_dimmed() -> None:
    entry = _entry(activation=Unavailable(reason="Missing"))

    assert row_presentation(entry=entry) == RowPresentation(
        subtitle="Missing",
        activatable=False,
        dimmed=True,
        show_reveal=False,
        show_fix=False,
    )


def test_row_presentation_empty_reason_uses_original_subtitle() -> None:
    entry = _entry(activation=Unavailable(reason=""))

    assert row_presentation(entry=entry).subtitle == "Original subtitle"


@pytest.mark.parametrize(("query", "title"), [("mic", "Nothing matches “mic”"), ("", "No matches")])
def test_empty_state_query_returns_exact_text(query: str, title: str) -> None:
    assert empty_state(query=query) == (
        title,
        "The palette finds Sysbar's own actions, scenes, clipboard "
        "entries and audio devices. Try “mic”, “dark” or “focus”.",
    )
