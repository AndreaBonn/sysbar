"""Catalogue commands rendered as palette rows."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from sysbar.app.commands import CommandId, CommandState
from sysbar.app.commands.actions import CommandHandlers
from sysbar.app.commands.catalogue import CATALOGUE
from sysbar.app.commands.models import Requirement
from sysbar.app.commands.palette import command_entries
from sysbar.services.palette.models import EntryKind


def _handlers(record: list[str]) -> CommandHandlers:
    def simple(name: str) -> Callable[[], None]:
        return lambda: record.append(name)

    def parametric(name: str) -> Callable[[str], None]:
        return lambda value: record.append(f"{name}:{value}")

    return CommandHandlers(
        simple={
            command.id: simple(command.id.value)
            for command in CATALOGUE
            if not command.is_parametric
        },
        parametric={
            command.id: parametric(command.id.value)
            for command in CATALOGUE
            if command.is_parametric
        },
    )


@pytest.fixture
def record() -> list[str]:
    return []


def test_every_non_parametric_command_gets_a_row(record: list[str]) -> None:
    entries = command_entries(_handlers(record), CommandState())

    expected = len([command for command in CATALOGUE if not command.is_parametric])
    assert len(entries) == expected


def test_parametric_commands_are_left_out(record: list[str]) -> None:
    ids = {entry.id for entry in command_entries(_handlers(record), CommandState())}

    assert "command:activate-scene" not in ids


def test_rows_are_tagged_as_commands(record: list[str]) -> None:
    entries = command_entries(_handlers(record), CommandState())

    assert all(entry.kind is EntryKind.COMMAND for entry in entries)


def test_an_available_command_is_runnable(record: list[str]) -> None:
    entries = command_entries(_handlers(record), CommandState())
    entry = next(e for e in entries if e.id == "command:open-panel")

    assert entry.is_runnable is True


def test_activating_a_row_invokes_the_command(record: list[str]) -> None:
    entries = command_entries(_handlers(record), CommandState())

    next(e for e in entries if e.id == "command:open-panel").activate()

    assert record == ["open-panel"]


def test_an_unavailable_command_is_listed_with_its_reason(record: list[str]) -> None:
    entries = command_entries(_handlers(record), CommandState(shelf_enabled=False))
    entry = next(e for e in entries if e.id == "command:open-shelf")

    assert entry.is_runnable is False
    assert "shelf" in entry.unavailable_reason.lower()


def test_an_unavailable_command_does_nothing_when_activated(record: list[str]) -> None:
    entries = command_entries(_handlers(record), CommandState(shelf_enabled=False))

    next(e for e in entries if e.id == "command:open-shelf").activate()

    assert record == []


def test_the_same_command_becomes_runnable_once_available(record: list[str]) -> None:
    entries = command_entries(_handlers(record), CommandState(shelf_enabled=True))
    entry = next(e for e in entries if e.id == "command:open-shelf")

    assert entry.is_runnable is True


def test_a_command_with_no_handler_is_unavailable(record: list[str]) -> None:
    complete = _handlers(record)
    without_quit = CommandHandlers(
        simple={k: v for k, v in complete.simple.items() if k is not CommandId.QUIT},
        parametric=complete.parametric,
    )

    entries = command_entries(without_quit, CommandState())
    entry = next(e for e in entries if e.id == "command:quit")

    assert entry.is_runnable is False


def test_the_subtitle_names_the_kind_of_command_not_its_internal_id(
    record: list[str],
) -> None:
    entries = command_entries(_handlers(record), CommandState())
    panel = next(e for e in entries if e.id == "command:open-panel")
    keep_awake = next(e for e in entries if e.id == "command:toggle-keep-awake")

    assert panel.subtitle == "Opens a window"
    assert keep_awake.subtitle == "Quick toggle"


def test_the_scriptable_name_stays_searchable(record: list[str]) -> None:
    entries = command_entries(_handlers(record), CommandState())
    entry = next(e for e in entries if e.id == "command:open-panel")

    assert "open-panel" in entry.haystack
    assert "Open the metrics panel" in entry.haystack


def test_a_turned_off_feature_offers_to_turn_it_on(record: list[str]) -> None:
    enabled: list[str] = []
    entries = command_entries(
        _handlers(record),
        CommandState(shelf_enabled=False),
        enablers={Requirement.SHELF_ENABLED: lambda: enabled.append("shelf")},
    )
    shelf = next(e for e in entries if e.id == "command:open-shelf")

    assert shelf.is_runnable is False
    assert shelf.fix_label == "Turn on"
    assert shelf.apply_fix() is True
    assert enabled == ["shelf"]


def test_an_unavailable_command_without_an_enabler_offers_no_fix(record: list[str]) -> None:
    entries = command_entries(_handlers(record), CommandState(shelf_enabled=False))
    shelf = next(e for e in entries if e.id == "command:open-shelf")

    assert shelf.fix_label == ""
    assert shelf.apply_fix() is False
