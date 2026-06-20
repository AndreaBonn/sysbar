"""Keep-awake global hotkey manager.

Decides whether to register the keep-awake shortcut (honouring the
``hotkey-enabled`` setting) and routes its activation to a callback. The
shortcuts backend is injected, so this decision is unit-tested without a portal.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from ...core.constants import KEEP_AWAKE_SHORTCUT_DESCRIPTION, KEEP_AWAKE_SHORTCUT_ID
from .ports import GlobalShortcuts

log = logging.getLogger(__name__)


class HotkeyManager:
    """Binds the keep-awake toggle to a global shortcut when enabled."""

    def __init__(
        self,
        shortcuts: GlobalShortcuts,
        on_trigger: Callable[[], None],
        enabled: Callable[[], bool],
    ) -> None:
        self._shortcuts = shortcuts
        self._on_trigger = on_trigger
        self._enabled = enabled

    def start(self) -> None:
        """Register the shortcut, unless the user has disabled the hotkey."""
        if not self._enabled():
            log.debug("global hotkey disabled; not binding")
            return
        self._shortcuts.bind(
            KEEP_AWAKE_SHORTCUT_ID, KEEP_AWAKE_SHORTCUT_DESCRIPTION, self._on_trigger
        )
