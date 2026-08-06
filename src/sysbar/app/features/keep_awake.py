"""Keep awake, including the tray countdown timer.

The countdown lives here rather than in the tray because its lifetime is tied to
the session, not to the label: it starts when a session with a visible countdown
begins and must be removed when the session ends, or the timer leaks and keeps
redrawing forever.
"""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib  # noqa: E402

from ...core.i18n import _  # noqa: E402
from ...services.keep_awake.inhibitor import SystemInhibitor  # noqa: E402
from ...services.keep_awake.manager import KeepAwakeManager  # noqa: E402
from ...services.keep_awake.ports import EndReason  # noqa: E402
from ...services.keep_awake.scheduler import GLibScheduler  # noqa: E402
from ...services.system_monitor.adapters import SysfsPowerReader  # noqa: E402
from .. import tray_state  # noqa: E402
from ..context import AppContext  # noqa: E402

_COUNTDOWN_TICK_SECONDS = 1
_NO_TIMER = 0
_SESSION_END_MESSAGES = {
    EndReason.TIMER.value: "Keep awake ended (timer elapsed)",
    EndReason.BATTERY.value: "Keep awake ended (battery low)",
}


class KeepAwakeFeature:
    """Owns the keep-awake manager and the tray countdown."""

    def __init__(
        self,
        context: AppContext,
        on_changed: Callable[[], None],
        on_tick: Callable[[], None],
    ) -> None:
        self._context = context
        self._on_changed = on_changed
        self._on_tick = on_tick
        self._countdown_timer = _NO_TIMER
        self._manager = KeepAwakeManager(SystemInhibitor(), SysfsPowerReader(), GLibScheduler())
        self._manager.connect("changed", self._on_manager_changed)
        self._manager.connect("session-ended", self._on_session_ended)

    @property
    def is_active(self) -> bool:
        return bool(self._manager.is_active)

    def toggle(self) -> None:
        config = self._context.config
        self._manager.toggle(
            duration_minutes=config.default_duration_minutes,
            clamshell=config.get_bool("clamshell-preferred"),
            battery_limit=config.battery_limit_percent,
        )

    def set_active(self, active: bool) -> None:
        """Drive the session to a target state; no-op if already there."""
        if self.is_active != active:
            self.toggle()

    def countdown_text(self) -> str:
        """The keep-awake segment of the tray label, empty when it has none."""
        return tray_state.countdown_text(
            active=self.is_active,
            show=self._context.config.get_bool("show-countdown"),
            remaining_seconds=self._manager.remaining_seconds() if self.is_active else None,
        )

    def _on_manager_changed(self, _manager: KeepAwakeManager) -> None:
        self._reconcile_countdown()
        self._on_changed()

    def _on_session_ended(self, _manager: KeepAwakeManager, reason: str) -> None:
        message = _SESSION_END_MESSAGES.get(reason)
        if message:
            self._context.notifier.notify("Sysbar", _(message), notification_id="keep-awake")

    def _reconcile_countdown(self) -> None:
        wants = self.is_active and self._context.config.get_bool("show-countdown")
        if wants and not self._countdown_timer:
            self._countdown_timer = GLib.timeout_add_seconds(
                _COUNTDOWN_TICK_SECONDS, self._on_countdown_tick
            )
        elif not wants and self._countdown_timer:
            GLib.source_remove(self._countdown_timer)
            self._countdown_timer = _NO_TIMER

    def _on_countdown_tick(self) -> bool:
        self._on_tick()
        if self.is_active:
            return True
        self._countdown_timer = _NO_TIMER
        return False
