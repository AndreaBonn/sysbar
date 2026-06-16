"""Interfaces for auto-quit.

The service depends only on these protocols; libwnck and ``os.kill`` are the
concrete implementations. Tests inject fakes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

# (window_id, app_id, pid) — app_id/pid may be None when the WM omits them.
WindowOpenedCallback = Callable[[int, str | None, int | None], None]
WindowClosedCallback = Callable[[int], None]


class WindowSource(Protocol):
    """Emits window open/close events for the current session."""

    def subscribe(
        self, on_opened: WindowOpenedCallback, on_closed: WindowClosedCallback
    ) -> None: ...


class Terminator(Protocol):
    """Terminates a process, escalating from SIGTERM to SIGKILL."""

    def terminate(self, pid: int) -> None: ...
    def force_kill(self, pid: int) -> None: ...
    def is_alive(self, pid: int) -> bool: ...


class Scheduler(Protocol):
    """Schedules and cancels delayed callbacks."""

    def schedule(self, seconds: float, callback: Callable[[], bool]) -> int: ...
    def cancel(self, handle: int) -> None: ...
