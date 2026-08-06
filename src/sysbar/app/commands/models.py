"""What a command is, and when it is available.

A command is a named thing the user can invoke, from the tray, the command line
or D-Bus. The set of them is a *constant*: that is what lets the same table feed
the tray without endangering its invariant, since a constant table cannot make
the menu's node count depend on runtime data.

Things with a variable cardinality, such as clipboard entries or audio devices,
are deliberately not commands. They are arguments to one, and will be surfaced
by their own providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CommandId(StrEnum):
    """Stable identifier of a command, and its D-Bus action name.

    These names are published on the session bus, so they are API: rename one
    and every script calling it breaks.
    """

    OPEN_PANEL = "open-panel"
    OPEN_PALETTE = "open-palette"
    OPEN_SETTINGS = "open-settings"
    OPEN_SHELF = "open-shelf"
    OPEN_CLIPBOARD = "open-clipboard"
    OPEN_UNINSTALLER = "open-uninstaller"
    TOGGLE_KEEP_AWAKE = "toggle-keep-awake"
    TOGGLE_MICROPHONE = "toggle-microphone"
    TOGGLE_DND = "toggle-dnd"
    TOGGLE_DARK_MODE = "toggle-dark-mode"
    TOGGLE_FOCUS_SCENE = "toggle-focus-scene"
    ACTIVATE_SCENE = "activate-scene"
    CLEAR_SCENE = "clear-scene"
    QUIT = "quit"


class Category(StrEnum):
    """Grouping used when commands are listed."""

    WINDOW = "window"
    TOGGLE = "toggle"
    SCENE = "scene"
    APPLICATION = "application"


class Requirement(StrEnum):
    """What must hold for a command to do anything."""

    ALWAYS = "always"
    MICROPHONE = "microphone"
    DESKTOP_TOGGLES = "desktop-toggles"
    SHELF_ENABLED = "shelf-enabled"
    CLIPBOARD_ENABLED = "clipboard-enabled"


# D-Bus type string of a command's parameter. ``None`` means it takes none.
PARAM_STRING = "s"


@dataclass(frozen=True)
class Command:
    """One invocable command."""

    id: CommandId
    title: str
    category: Category
    requires: Requirement = Requirement.ALWAYS
    parameter_type: str | None = None

    @property
    def is_parametric(self) -> bool:
        return self.parameter_type is not None


@dataclass(frozen=True)
class CommandState:
    """The runtime facts a requirement is checked against.

    A plain record rather than a reference to the live features: availability is
    then a pure function, and the same answer can be computed for the tray, the
    command line and a test.
    """

    has_microphone: bool = False
    has_desktop_toggles: bool = False
    shelf_enabled: bool = False
    clipboard_enabled: bool = False


_REASONS = {
    Requirement.MICROPHONE: "No microphone available",
    Requirement.DESKTOP_TOGGLES: "Not available outside a GNOME session",
    Requirement.SHELF_ENABLED: "The shelf is turned off in settings",
    Requirement.CLIPBOARD_ENABLED: "Clipboard history is turned off in settings",
}


def is_available(command: Command, state: CommandState) -> bool:
    """Whether invoking ``command`` right now would do anything."""
    match command.requires:
        case Requirement.ALWAYS:
            return True
        case Requirement.MICROPHONE:
            return state.has_microphone
        case Requirement.DESKTOP_TOGGLES:
            return state.has_desktop_toggles
        case Requirement.SHELF_ENABLED:
            return state.shelf_enabled
        case Requirement.CLIPBOARD_ENABLED:
            return state.clipboard_enabled


def unavailable_reason(command: Command) -> str:
    """Why a command is unavailable, for surfaces that say so rather than hide it.

    Returned untranslated: the tray hides unavailable commands and never shows
    this, and the command line is not localised. The palette translates it at
    the point of display.
    """
    return _REASONS.get(command.requires, "")
