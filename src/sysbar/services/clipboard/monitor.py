"""Live clipboard listener (the Gdk boundary).

Subscribes to the default :class:`Gdk.Clipboard` ``changed`` signal, reads the
new text asynchronously and forwards it to a callback. Boundary code exercised
manually (a display and clipboard are required), so it carries no unit tests;
the history logic it feeds lives in :class:`ClipboardService`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib  # noqa: E402

log = logging.getLogger(__name__)


class ClipboardMonitor:  # pragma: no cover - Gdk clipboard boundary
    """Forwards each new clipboard text selection to a callback."""

    def __init__(self, on_text: Callable[[str], None]) -> None:
        self._on_text = on_text
        self._clipboard: Any = None

    def start(self) -> bool:
        """Begin listening; return ``False`` if no display is available."""
        display = Gdk.Display.get_default()
        if display is None:
            log.warning("clipboard monitor unavailable: no display")
            return False
        self._clipboard = display.get_clipboard()
        self._clipboard.connect("changed", self._on_changed)
        return True

    def _on_changed(self, clipboard: Any) -> None:
        clipboard.read_text_async(None, self._on_read)

    def _on_read(self, clipboard: Any, result: Any) -> None:
        try:
            text = clipboard.read_text_finish(result)
        except GLib.Error:
            return
        if text:
            self._on_text(text)
