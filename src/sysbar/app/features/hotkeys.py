"""Global shortcuts, registered through the desktop portal.

The bindings themselves are supplied by the caller, because each one points at
a different feature; this module only owns the portal session and the decision
of whether shortcuts are possible at all in this session.
"""

from __future__ import annotations

import logging

from ...core.capabilities import GLOBAL_SHORTCUTS
from ...services.hotkey.manager import HotkeyBinding, HotkeyManager
from ..context import AppContext

log = logging.getLogger(__name__)


class HotkeyFeature:
    """Owns the portal shortcuts session, if the session supports one."""

    def __init__(self, context: AppContext, bindings: list[HotkeyBinding]) -> None:
        self._manager: HotkeyManager | None = None
        if not context.has(GLOBAL_SHORTCUTS):
            return
        try:
            from ...services.hotkey.portal import PortalGlobalShortcuts

            shortcuts = PortalGlobalShortcuts()
        except Exception as error:
            log.warning("global shortcuts unavailable", extra={"error": str(error)})
            return
        self._manager = HotkeyManager(shortcuts, bindings)
        self._manager.start()

    @property
    def is_available(self) -> bool:
        return self._manager is not None
