"""The full command table.

One constant, consumed by the D-Bus action group, the command line and the
palette, so that a command cannot exist on one surface and be missing from
another. Adding a command here makes it scriptable; wiring its handler is
enforced by a test that requires every :class:`CommandId` to have one.
"""

from __future__ import annotations

from .models import Category, Command, CommandId, Requirement

CATALOGUE: tuple[Command, ...] = (
    Command(
        id=CommandId.OPEN_PANEL,
        title="Open the metrics panel",
        category=Category.WINDOW,
    ),
    Command(
        id=CommandId.OPEN_SETTINGS,
        title="Open settings",
        category=Category.WINDOW,
    ),
    Command(
        id=CommandId.OPEN_SHELF,
        title="Open the shelf",
        category=Category.WINDOW,
        requires=Requirement.SHELF_ENABLED,
    ),
    Command(
        id=CommandId.OPEN_CLIPBOARD,
        title="Open clipboard history",
        category=Category.WINDOW,
        requires=Requirement.CLIPBOARD_ENABLED,
    ),
    Command(
        id=CommandId.OPEN_UNINSTALLER,
        title="Open the application uninstaller",
        category=Category.WINDOW,
    ),
    Command(
        id=CommandId.TOGGLE_KEEP_AWAKE,
        title="Toggle keep awake",
        category=Category.TOGGLE,
    ),
    Command(
        id=CommandId.TOGGLE_MICROPHONE,
        title="Mute or unmute the microphone",
        category=Category.TOGGLE,
        requires=Requirement.MICROPHONE,
    ),
    Command(
        id=CommandId.TOGGLE_DND,
        title="Turn Do Not Disturb on or off",
        category=Category.TOGGLE,
        requires=Requirement.DESKTOP_TOGGLES,
    ),
    Command(
        id=CommandId.TOGGLE_DARK_MODE,
        title="Switch between light and dark",
        category=Category.TOGGLE,
        requires=Requirement.DESKTOP_TOGGLES,
    ),
    Command(
        id=CommandId.TOGGLE_FOCUS_SCENE,
        title="Toggle the Focus scene",
        category=Category.SCENE,
    ),
    Command(
        id=CommandId.ACTIVATE_SCENE,
        title="Activate a scene by id",
        category=Category.SCENE,
        parameter_type="s",
    ),
    Command(
        id=CommandId.CLEAR_SCENE,
        title="Clear the active scene",
        category=Category.SCENE,
    ),
    Command(
        id=CommandId.QUIT,
        title="Quit Sysbar",
        category=Category.APPLICATION,
    ),
)

_BY_ID = {command.id: command for command in CATALOGUE}


def command_ids() -> tuple[str, ...]:
    """Every command name, in catalogue order."""
    return tuple(command.id.value for command in CATALOGUE)


def find(command_id: str) -> Command | None:
    """The command with this name, or ``None`` if there is no such command."""
    try:
        return _BY_ID[CommandId(command_id)]
    except ValueError:
        return None
