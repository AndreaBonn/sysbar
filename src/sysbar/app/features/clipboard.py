"""Clipboard history: the store, the capture listener and the window.

Off by default, and deliberately so: the history is kept in plain text on disk.
Nothing is captured until the setting is enabled, at which point the listener
starts and the store is read.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk  # noqa: E402

from ...core.constants import CLIPBOARD_DIR  # noqa: E402
from ...services.clipboard.models import ClipEntry  # noqa: E402
from ...services.clipboard.monitor import ClipboardMonitor  # noqa: E402
from ...services.clipboard.service import ClipboardService  # noqa: E402
from ..context import AppContext  # noqa: E402
from ..windows import WindowSlot  # noqa: E402

if TYPE_CHECKING:
    from ...ui.clipboard.clipboard_window import ClipboardWindow

_ENABLED_KEY = "clipboard-enabled"


class ClipboardFeature:
    """Owns the clipboard history, its capture listener and its window."""

    def __init__(self, context: AppContext) -> None:
        self._context = context
        self._service: ClipboardService | None = None
        self._monitor: ClipboardMonitor | None = None
        self._window: WindowSlot[ClipboardWindow] = WindowSlot(self._build_window)

    @property
    def is_enabled(self) -> bool:
        return self._context.config.get_bool(_ENABLED_KEY)

    def reconcile(self) -> None:
        """Start capturing once the feature is switched on."""
        if not self.is_enabled or self._monitor is not None:
            return
        self._ensure_service()
        monitor = ClipboardMonitor(on_text=self._capture)
        if monitor.start():
            self._monitor = monitor

    def open(self) -> None:
        self._window.present()

    def entries(self) -> list[ClipEntry]:
        """The history, or nothing at all while the feature is switched off.

        Deliberately does not build the store: asking what is in a disabled
        history should not be what causes it to start being kept.
        """
        if not self.is_enabled or self._service is None:
            return []
        return self._service.items

    def copy(self, text: str) -> None:
        """Put ``text`` back on the system clipboard."""
        self._copy_back(text)

    def _ensure_service(self) -> ClipboardService:
        if self._service is None:
            self._service = ClipboardService(CLIPBOARD_DIR)
            self._service.load()
        return self._service

    def _build_window(self) -> ClipboardWindow:
        from ...ui.clipboard.clipboard_window import ClipboardWindow

        return ClipboardWindow(self._ensure_service(), self._copy_back)

    def _capture(self, text: str) -> None:
        self._ensure_service().capture(text)

    def _copy_back(self, text: str) -> None:
        """Put a history entry back on the system clipboard."""
        display = Gdk.Display.get_default()
        if display is not None:
            display.get_clipboard().set(text)
