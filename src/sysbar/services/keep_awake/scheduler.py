"""GLib-backed scheduler adapter."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib  # noqa: E402


class GLibScheduler:
    """Schedules repeating/one-shot callbacks on the GLib main loop."""

    def schedule(self, seconds: float, callback: Callable[[], bool]) -> int:
        return int(GLib.timeout_add_seconds(max(1, int(seconds)), callback))

    def cancel(self, handle: int) -> None:
        GLib.source_remove(handle)
