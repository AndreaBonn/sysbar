"""The drop shelf, its window and the optional shake-to-open gesture.

The service is built on first need rather than at startup: the feature ships
disabled, and a user who never turns it on should not pay for reading its
manifest. Shake detection is reconciled separately because it depends on both
the feature switch and an X11 session.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from ...core.capabilities import SESSION_X11  # noqa: E402
from ...core.constants import SHELF_DIR  # noqa: E402
from ...services.shelf.models import ShelfItem  # noqa: E402
from ...services.shelf.shake_monitor import ShakeMonitor  # noqa: E402
from ...services.shelf.shelf_service import ShelfService  # noqa: E402
from ..context import AppContext  # noqa: E402
from ..windows import WindowSlot  # noqa: E402

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ...ui.shelf.shelf_window import ShelfWindow

_ENABLED_KEY = "shelf-enabled"
_SHAKE_KEY = "shelf-shake-to-open"


class ShelfFeature:
    """Owns the shelf service, its window and the shake monitor."""

    def __init__(self, context: AppContext) -> None:
        self._context = context
        self._service: ShelfService | None = None
        self._shake: ShakeMonitor | None = None
        self._window: WindowSlot[ShelfWindow] = WindowSlot(self._build_window)

    @property
    def is_enabled(self) -> bool:
        return self._context.config.get_bool(_ENABLED_KEY)

    def reconcile(self) -> None:
        """Match the running shelf and shake monitor to the current settings."""
        if self.is_enabled:
            self._ensure_service()
        self._reconcile_shake()

    def open(self) -> None:
        self._window.present()

    def items(self) -> list[ShelfItem]:
        """What is on the shelf, or nothing while the feature is switched off."""
        if not self.is_enabled or self._service is None:
            return []
        return self._service.items

    def open_uri(self, uri: str) -> None:
        """Hand a shelf item to the desktop's default application."""
        try:
            Gio.AppInfo.launch_default_for_uri(uri, None)
        except GLib.Error:
            log.warning("could not open shelf item", extra={"uri": uri})

    def _ensure_service(self) -> ShelfService:
        if self._service is None:
            self._service = ShelfService(SHELF_DIR)
            self._service.load()
        return self._service

    def _build_window(self) -> ShelfWindow:
        from ...ui.shelf.shelf_window import ShelfWindow

        return ShelfWindow(self._ensure_service())

    def _reconcile_shake(self) -> None:
        wants = (
            self.is_enabled
            and self._context.config.get_bool(_SHAKE_KEY)
            and self._context.has(SESSION_X11)
        )
        if wants and self._shake is None:
            monitor = ShakeMonitor(on_shake=self.open)
            if monitor.start():
                self._shake = monitor
        elif not wants and self._shake is not None:
            self._shake.stop()
            self._shake = None
