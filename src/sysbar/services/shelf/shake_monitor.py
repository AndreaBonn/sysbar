"""X11 pointer-shake monitor.

Polls the global pointer position via ``XQueryPointer`` and feeds deltas to a
:class:`ShakeDetector`. On a shake it invokes the callback on the GLib main
loop. Requires an X11 session; boundary code, exercised manually.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib  # noqa: E402

from ...core.constants import SHAKE_POLL_MS  # noqa: E402
from .shake_detector import ShakeDetector  # noqa: E402

log = logging.getLogger(__name__)


class ShakeMonitor:
    """Detect a pointer shake by polling the X11 root pointer position."""

    def __init__(self, on_shake: Callable[[], None]) -> None:
        self._on_shake = on_shake
        self._detector = ShakeDetector()
        self._root: Any = None
        self._timer = 0
        self._last: tuple[int, int] | None = None

    def start(self) -> bool:
        """Begin polling; return ``False`` if X11 is unavailable."""
        try:
            from Xlib import display

            self._root = display.Display().screen().root  # pragma: no cover - requires X11
        except Exception as error:
            log.warning("shake monitor unavailable", extra={"error": str(error)})
            return False
        self._timer = GLib.timeout_add(SHAKE_POLL_MS, self._tick)  # pragma: no cover - requires X11
        return True  # pragma: no cover - requires X11

    def stop(self) -> None:
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = 0
        self._last = None
        self._detector.reset()

    def _tick(self) -> bool:
        if self._root is None:
            return False
        pointer = self._root.query_pointer()
        x, y = pointer.root_x, pointer.root_y
        now = time.monotonic()
        if self._last is not None:
            dx = float(x - self._last[0])
            if self._detector.feed(dx, now):
                GLib.idle_add(self._fire)
        self._last = (x, y)
        return True

    def _fire(self) -> bool:
        self._on_shake()
        return False
