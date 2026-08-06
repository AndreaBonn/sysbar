"""Binding catalogue entries to the features that carry them out.

Kept out of ``application.py`` on purpose: this table grows by one line per new
command, and that is exactly the kind of growth the application module is not
supposed to absorb.
"""

from __future__ import annotations

from collections.abc import Callable

from ..features import Features
from .actions import CommandHandlers
from .models import CommandId, CommandState


def build_handlers(
    features: Features, open_settings: Callable[[], None], quit_application: Callable[[], None]
) -> CommandHandlers:
    """Route every command to its feature.

    Only settings and quit come from the application; everything else is a
    method on the feature that owns the behaviour, so a command cannot drift
    away from the thing it invokes.
    """
    return CommandHandlers(
        simple={
            CommandId.OPEN_PANEL: features.panel.open,
            CommandId.OPEN_PALETTE: features.palette.open,
            CommandId.OPEN_SETTINGS: open_settings,
            CommandId.OPEN_SHELF: features.shelf.open,
            CommandId.OPEN_CLIPBOARD: features.clipboard.open,
            CommandId.OPEN_UNINSTALLER: features.uninstaller.open,
            CommandId.TOGGLE_KEEP_AWAKE: features.keep_awake.toggle,
            CommandId.TOGGLE_MICROPHONE: features.toggles.toggle_microphone,
            CommandId.TOGGLE_DND: features.toggles.toggle_do_not_disturb,
            CommandId.TOGGLE_DARK_MODE: features.toggles.toggle_dark_mode,
            CommandId.OPEN_SCENES: features.scenes.open,
            CommandId.TOGGLE_FOCUS_SCENE: features.scenes.toggle_focus,
            CommandId.CLEAR_SCENE: features.scenes.clear,
            CommandId.QUIT: quit_application,
        },
        parametric={CommandId.ACTIVATE_SCENE: features.scenes.activate},
    )


def current_state(features: Features) -> CommandState:
    """Snapshot the facts that decide which commands can do anything now."""
    toggles = features.toggles.state()
    return CommandState(
        has_microphone=toggles.mic_available,
        has_desktop_toggles=toggles.dnd_available,
        shelf_enabled=features.shelf.is_enabled,
        clipboard_enabled=features.clipboard.is_enabled,
    )
