"""Keep-awake session manager (port of ``KeepAwakeManager``).

Holds sleep/idle (and optionally lid) inhibitions for the session duration, ends
on timer or when the battery drops below a threshold, and notifies subscribers
through GObject signals. Inhibitor, battery source, scheduler and clock are
injected, so the session logic is unit-tested without D-Bus or real timers.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import ClassVar

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GObject  # noqa: E402

from ...core.constants import BATTERY_WATCHDOG_INTERVAL_SECONDS  # noqa: E402
from .ports import BatterySource, EndReason, Inhibitor, InhibitorToken, Scheduler  # noqa: E402

log = logging.getLogger(__name__)

WHAT_IDLE_SLEEP = "idle:sleep"
WHAT_LID = "handle-lid-switch"
_SECONDS_PER_MINUTE = 60


class KeepAwakeManager(GObject.Object):
    """Owns the current keep-awake session and its inhibitions."""

    __gsignals__: ClassVar[dict[str, tuple[object, ...]]] = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "session-ended": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(
        self,
        inhibitor: Inhibitor,
        battery: BatterySource,
        scheduler: Scheduler,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__()
        self._inhibitor = inhibitor
        self._battery = battery
        self._scheduler = scheduler
        self._clock = clock or datetime.now
        self._active = False
        self._end_date: datetime | None = None
        self._battery_limit = 0
        self._tokens: list[InhibitorToken] = []
        self._timer: int | None = None
        self._battery_timer: int | None = None

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def end_date(self) -> datetime | None:
        return self._end_date

    def remaining_seconds(self) -> float | None:
        """Seconds left in a timed session, or ``None`` if indefinite/inactive."""
        if self._end_date is None:
            return None
        return max(0.0, (self._end_date - self._clock()).total_seconds())

    def start(self, duration_minutes: int, clamshell: bool, battery_limit: int) -> None:
        """Begin a session; replaces any running one."""
        if self._active:
            self._teardown()
        self._acquire(clamshell)
        self._active = True
        self._battery_limit = battery_limit
        if duration_minutes > 0:
            self._end_date = self._clock() + timedelta(minutes=duration_minutes)
            self._timer = self._scheduler.schedule(
                duration_minutes * _SECONDS_PER_MINUTE, self._on_timer
            )
        if battery_limit > 0:
            self._battery_timer = self._scheduler.schedule(
                BATTERY_WATCHDOG_INTERVAL_SECONDS, self._on_battery_tick
            )
        self.emit("changed")

    def stop(self, reason: EndReason) -> None:
        """End the current session, releasing inhibitions."""
        if not self._active:
            return
        self._teardown()
        self.emit("changed")
        self.emit("session-ended", reason.value)

    def toggle(self, duration_minutes: int, clamshell: bool, battery_limit: int) -> None:
        if self._active:
            self.stop(EndReason.MANUAL)
        else:
            self.start(duration_minutes, clamshell, battery_limit)

    def _on_timer(self) -> bool:
        self._timer = None
        self.stop(EndReason.TIMER)
        return False

    def _on_battery_tick(self) -> bool:
        if self._should_stop_for_battery():
            self._battery_timer = None
            self.stop(EndReason.BATTERY)
            return False
        return True

    def _should_stop_for_battery(self) -> bool:
        if self._battery_limit <= 0 or not self._battery.on_battery():
            return False
        percent = self._battery.battery_percent()
        return percent is not None and percent < self._battery_limit

    def _acquire(self, clamshell: bool) -> None:
        self._add_token(self._inhibitor.acquire(WHAT_IDLE_SLEEP))
        if clamshell:
            self._add_token(self._inhibitor.acquire(WHAT_LID))

    def _add_token(self, token: InhibitorToken | None) -> None:
        if token is not None:
            self._tokens.append(token)

    def _teardown(self) -> None:
        for token in self._tokens:
            self._inhibitor.release(token)
        self._tokens.clear()
        for handle in (self._timer, self._battery_timer):
            if handle is not None:
                self._scheduler.cancel(handle)
        self._timer = None
        self._battery_timer = None
        self._active = False
        self._end_date = None
