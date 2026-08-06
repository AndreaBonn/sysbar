"""The catalogue is API: these tests pin what scripts can rely on."""

from __future__ import annotations

import pytest

from sysbar.app.commands import (
    CATALOGUE,
    Command,
    CommandId,
    CommandState,
    Requirement,
    command_ids,
    find,
    is_available,
    unavailable_reason,
)


def test_every_command_id_appears_exactly_once() -> None:
    ids = [command.id for command in CATALOGUE]

    assert sorted(ids) == sorted(CommandId)
    assert len(ids) == len(set(ids))


def test_every_command_has_a_title() -> None:
    assert all(command.title for command in CATALOGUE)


def test_command_ids_are_the_published_names() -> None:
    names = command_ids()

    assert "open-panel" in names
    assert "activate-scene" in names
    assert len(names) == len(CATALOGUE)


def test_find_returns_the_matching_command() -> None:
    command = find("open-panel")

    assert command is not None
    assert command.id is CommandId.OPEN_PANEL


def test_find_returns_none_for_an_unknown_name() -> None:
    assert find("definitely-not-a-command") is None


def test_find_returns_none_for_the_empty_name() -> None:
    assert find("") is None


def test_only_activate_scene_takes_a_parameter() -> None:
    parametric = [command.id for command in CATALOGUE if command.is_parametric]

    assert parametric == [CommandId.ACTIVATE_SCENE]


def test_activate_scene_takes_a_string() -> None:
    command = find("activate-scene")

    assert command is not None
    assert command.parameter_type == "s"


# --- availability ---------------------------------------------------------


def _command(requires: Requirement) -> Command:
    return next(command for command in CATALOGUE if command.requires is requires)


def test_unconditional_commands_are_always_available() -> None:
    assert is_available(_command(Requirement.ALWAYS), CommandState()) is True


def test_microphone_command_needs_a_microphone() -> None:
    command = _command(Requirement.MICROPHONE)

    assert is_available(command, CommandState(has_microphone=False)) is False
    assert is_available(command, CommandState(has_microphone=True)) is True


def test_desktop_toggle_needs_a_gnome_session() -> None:
    command = _command(Requirement.DESKTOP_TOGGLES)

    assert is_available(command, CommandState(has_desktop_toggles=False)) is False
    assert is_available(command, CommandState(has_desktop_toggles=True)) is True


def test_shelf_command_follows_the_shelf_setting() -> None:
    command = _command(Requirement.SHELF_ENABLED)

    assert is_available(command, CommandState(shelf_enabled=False)) is False
    assert is_available(command, CommandState(shelf_enabled=True)) is True


def test_clipboard_command_follows_the_clipboard_setting() -> None:
    command = _command(Requirement.CLIPBOARD_ENABLED)

    assert is_available(command, CommandState(clipboard_enabled=False)) is False
    assert is_available(command, CommandState(clipboard_enabled=True)) is True


def test_one_requirement_does_not_satisfy_another() -> None:
    microphone = _command(Requirement.MICROPHONE)

    assert is_available(microphone, CommandState(shelf_enabled=True)) is False


@pytest.mark.parametrize(
    "requirement",
    [
        Requirement.MICROPHONE,
        Requirement.DESKTOP_TOGGLES,
        Requirement.SHELF_ENABLED,
        Requirement.CLIPBOARD_ENABLED,
    ],
)
def test_every_conditional_requirement_explains_itself(requirement: Requirement) -> None:
    assert unavailable_reason(_command(requirement))


def test_an_unconditional_command_has_no_reason_to_give() -> None:
    assert unavailable_reason(_command(Requirement.ALWAYS)) == ""
