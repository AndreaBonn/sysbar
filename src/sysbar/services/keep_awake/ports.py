"""Interfaces and value types for keep-awake.

The manager depends only on these protocols, so the session/timer/battery logic
is tested with fakes (no real D-Bus inhibitors or GLib timers).
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Protocol

# A handle returned by an inhibitor when an inhibition is taken; opaque to us.
InhibitorToken = object


class EndReason(StrEnum):
    """Why a keep-awake session ended."""

    MANUAL = "manual"
    TIMER = "timer"
    BATTERY = "battery"
    QUIT = "quit"


class Inhibitor(Protocol):
    """Acquires and releases system sleep/idle/lid inhibitions."""

    def acquire(self, what: str) -> InhibitorToken | None: ...
    def release(self, token: InhibitorToken) -> None: ...


class BatterySource(Protocol):
    """Reports battery charge and whether the system runs on battery."""

    def battery_percent(self) -> float | None: ...
    def on_battery(self) -> bool | None: ...


class Scheduler(Protocol):
    """Schedules and cancels delayed callbacks (abstracts ``GLib`` timers)."""

    def schedule(self, seconds: float, callback: Callable[[], bool]) -> int: ...
    def cancel(self, handle: int) -> None: ...
