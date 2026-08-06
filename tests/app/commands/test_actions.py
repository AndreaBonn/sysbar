"""Behaviour of the D-Bus action group built from the catalogue."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
import pytest  # noqa: E402
from gi.repository import Gio, GLib  # noqa: E402

from sysbar.app.commands import CommandId, CommandState  # noqa: E402
from sysbar.app.commands.actions import (  # noqa: E402
    CommandHandlers,
    install_actions,
    refresh_enabled,
)
from sysbar.app.commands.catalogue import CATALOGUE  # noqa: E402


class _FakeTarget:
    def __init__(self) -> None:
        self.added: list[Gio.Action] = []

    def add_action(self, action: Gio.Action) -> None:
        self.added.append(action)


def _handlers(record: list[str]) -> CommandHandlers:
    """A complete handler map recording which command fired."""

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


# --- completeness ---------------------------------------------------------


def test_a_complete_handler_map_reports_nothing_missing(record: list[str]) -> None:
    assert _handlers(record).missing() == []
    assert _handlers(record).misplaced() == []


def test_a_missing_handler_is_refused_at_install(record: list[str]) -> None:
    complete = _handlers(record)
    incomplete = CommandHandlers(
        simple={k: v for k, v in complete.simple.items() if k is not CommandId.QUIT},
        parametric=complete.parametric,
    )

    with pytest.raises(ValueError, match="quit"):
        install_actions(_FakeTarget(), incomplete, CommandState())


def test_a_parametric_command_wired_as_simple_is_refused(record: list[str]) -> None:
    complete = _handlers(record)
    misplaced = CommandHandlers(
        simple={**complete.simple, CommandId.ACTIVATE_SCENE: lambda: None},
        parametric={},
    )

    with pytest.raises(ValueError, match="activate-scene"):
        install_actions(_FakeTarget(), misplaced, CommandState())


# --- registration ---------------------------------------------------------


def test_every_catalogue_command_is_registered(record: list[str]) -> None:
    target = _FakeTarget()

    actions = install_actions(target, _handlers(record), CommandState())

    assert len(target.added) == len(CATALOGUE)
    assert set(actions) == {command.id for command in CATALOGUE}


def test_unavailable_commands_are_registered_but_disabled(record: list[str]) -> None:
    actions = install_actions(_FakeTarget(), _handlers(record), CommandState(shelf_enabled=False))

    assert actions[CommandId.OPEN_SHELF].get_enabled() is False


def test_available_commands_are_enabled(record: list[str]) -> None:
    actions = install_actions(_FakeTarget(), _handlers(record), CommandState(shelf_enabled=True))

    assert actions[CommandId.OPEN_SHELF].get_enabled() is True


def test_unconditional_commands_are_enabled_with_nothing_available(record: list[str]) -> None:
    actions = install_actions(_FakeTarget(), _handlers(record), CommandState())

    assert actions[CommandId.OPEN_PANEL].get_enabled() is True


def test_refresh_enabled_follows_a_settings_change(record: list[str]) -> None:
    actions = install_actions(_FakeTarget(), _handlers(record), CommandState(shelf_enabled=False))

    refresh_enabled(actions, CommandState(shelf_enabled=True))

    assert actions[CommandId.OPEN_SHELF].get_enabled() is True


# --- dispatch -------------------------------------------------------------


def test_activating_a_simple_action_calls_its_handler(record: list[str]) -> None:
    actions = install_actions(_FakeTarget(), _handlers(record), CommandState())

    actions[CommandId.OPEN_PANEL].activate(None)

    assert record == ["open-panel"]


def test_activating_a_parametric_action_passes_the_argument(record: list[str]) -> None:
    actions = install_actions(_FakeTarget(), _handlers(record), CommandState())

    actions[CommandId.ACTIVATE_SCENE].activate(GLib.Variant("s", "focus"))

    assert record == ["activate-scene:focus"]


def test_a_parametric_action_refuses_an_empty_argument(record: list[str]) -> None:
    actions = install_actions(_FakeTarget(), _handlers(record), CommandState())

    actions[CommandId.ACTIVATE_SCENE].activate(GLib.Variant("s", ""))

    assert record == []


def test_glib_itself_drops_an_activation_with_no_argument(record: list[str]) -> None:
    """GLib refuses this before dispatch, so the handler is never reached.

    Asserted so the layering is explicit: the check inside ``_string_argument``
    is not what stops this case, and removing it would not show up here.
    """
    actions = install_actions(_FakeTarget(), _handlers(record), CommandState())

    actions[CommandId.ACTIVATE_SCENE].activate(None)

    assert record == []


def test_the_receiver_refuses_a_missing_argument() -> None:
    """The receiving end still checks, since the bus is not the only caller."""
    from sysbar.app.commands.actions import _string_argument
    from sysbar.app.commands.catalogue import find

    command = find("activate-scene")
    assert command is not None

    assert _string_argument(command, None) is None


def test_a_parametric_action_refuses_an_argument_of_the_wrong_type(record: list[str]) -> None:
    """Anything on the session bus can call this, so the type is checked here."""
    from sysbar.app.commands.actions import _string_argument
    from sysbar.app.commands.catalogue import find

    command = find("activate-scene")
    assert command is not None

    assert _string_argument(command, GLib.Variant("i", 42)) is None


def test_a_parametric_action_accepts_a_well_formed_argument() -> None:
    from sysbar.app.commands.actions import _string_argument
    from sysbar.app.commands.catalogue import find

    command = find("activate-scene")
    assert command is not None

    assert _string_argument(command, GLib.Variant("s", "focus")) == "focus"
