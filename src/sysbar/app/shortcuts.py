"""Which global shortcuts exist, and the setting that gates each one.

Kept apart from the portal session (:mod:`sysbar.app.features.hotkeys`) and from
the application: the table is a value, so the pairing of shortcut id, target and
enabling key is checkable without a desktop portal.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..core.config import Config
from ..core.constants import (
    CLIPBOARD_SHORTCUT_DESCRIPTION,
    CLIPBOARD_SHORTCUT_ID,
    FOCUS_SCENE_SHORTCUT_DESCRIPTION,
    FOCUS_SCENE_SHORTCUT_ID,
    KEEP_AWAKE_SHORTCUT_DESCRIPTION,
    KEEP_AWAKE_SHORTCUT_ID,
    SHELF_SHORTCUT_DESCRIPTION,
    SHELF_SHORTCUT_ID,
)
from ..services.hotkey.manager import HotkeyBinding

KEEP_AWAKE_ENABLED_KEY = "hotkey-enabled"
SHELF_ENABLED_KEY = "hotkey-shelf-enabled"
CLIPBOARD_ENABLED_KEY = "hotkey-clipboard-enabled"
FOCUS_SCENE_ENABLED_KEY = "hotkey-focus-scene-enabled"


@dataclass(frozen=True)
class ShortcutTargets:
    """What each global shortcut invokes."""

    toggle_keep_awake: Callable[[], None]
    open_shelf: Callable[[], None]
    open_clipboard: Callable[[], None]
    toggle_focus_scene: Callable[[], None]


def build_hotkey_bindings(config: Config, targets: ShortcutTargets) -> list[HotkeyBinding]:
    """The full shortcut table, each entry gated by its own settings key."""
    table = (
        (
            KEEP_AWAKE_SHORTCUT_ID,
            KEEP_AWAKE_SHORTCUT_DESCRIPTION,
            targets.toggle_keep_awake,
            KEEP_AWAKE_ENABLED_KEY,
        ),
        (SHELF_SHORTCUT_ID, SHELF_SHORTCUT_DESCRIPTION, targets.open_shelf, SHELF_ENABLED_KEY),
        (
            CLIPBOARD_SHORTCUT_ID,
            CLIPBOARD_SHORTCUT_DESCRIPTION,
            targets.open_clipboard,
            CLIPBOARD_ENABLED_KEY,
        ),
        (
            FOCUS_SCENE_SHORTCUT_ID,
            FOCUS_SCENE_SHORTCUT_DESCRIPTION,
            targets.toggle_focus_scene,
            FOCUS_SCENE_ENABLED_KEY,
        ),
    )
    return [
        HotkeyBinding(shortcut_id, description, trigger, _gate(config, key))
        for shortcut_id, description, trigger, key in table
    ]


def _gate(config: Config, key: str) -> Callable[[], bool]:
    """A predicate reading ``key`` at call time, not at build time."""
    return lambda: config.get_bool(key)
