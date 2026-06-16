"""Auto-quit service (port of ``AutoQuitService``).

Tracks windows per application; when an app's last window closes, after a grace
period (to tolerate apps that immediately reopen a window) it sends SIGTERM,
then escalates to SIGKILL if the process survives. Excepted and system apps are
never touched. Window source, terminator and scheduler are injected, so the
decision logic is unit-tested without a real session.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from ...core.constants import AUTO_QUIT_GRACE_SECONDS, AUTO_QUIT_KILL_TIMEOUT_SECONDS
from .ports import Scheduler, Terminator, WindowSource

log = logging.getLogger(__name__)


class AutoQuitService:
    """Terminate applications when their last window closes."""

    def __init__(
        self,
        source: WindowSource,
        terminator: Terminator,
        scheduler: Scheduler,
        exceptions: Callable[[], list[str]],
        system_ids: frozenset[str],
        enabled: Callable[[], bool] | None = None,
        grace_seconds: float = AUTO_QUIT_GRACE_SECONDS,
        kill_timeout_seconds: float = AUTO_QUIT_KILL_TIMEOUT_SECONDS,
    ) -> None:
        self._source = source
        self._terminator = terminator
        self._scheduler = scheduler
        self._exceptions = exceptions
        self._system_ids = system_ids
        self._enabled = enabled or (lambda: True)
        self._grace = grace_seconds
        self._kill_timeout = kill_timeout_seconds
        self._window_app: dict[int, str] = {}
        self._app_windows: dict[str, set[int]] = {}
        self._app_pid: dict[str, int] = {}
        self._grace_timers: dict[str, int] = {}
        self._kill_timers: dict[str, int] = {}

    def start(self) -> None:
        self._source.subscribe(self.handle_window_opened, self.handle_window_closed)

    def handle_window_opened(self, window_id: int, app_id: str | None, pid: int | None) -> None:
        if app_id is None:
            return
        self._window_app[window_id] = app_id
        self._app_windows.setdefault(app_id, set()).add(window_id)
        if pid is not None:
            self._app_pid[app_id] = pid
        self._cancel_grace(app_id)

    def handle_window_closed(self, window_id: int) -> None:
        app_id = self._window_app.pop(window_id, None)
        if app_id is None:
            return
        windows = self._app_windows.get(app_id)
        if windows is None:
            return
        windows.discard(window_id)
        if not windows:
            self._app_windows.pop(app_id, None)
            self._maybe_schedule_termination(app_id)

    def _maybe_schedule_termination(self, app_id: str) -> None:
        if not self._enabled():
            return
        if app_id in self._system_ids or app_id in self._exceptions():
            return
        if app_id not in self._app_pid or app_id in self._grace_timers:
            return
        self._grace_timers[app_id] = self._scheduler.schedule(
            self._grace, lambda: self._terminate(app_id)
        )

    def _terminate(self, app_id: str) -> bool:
        self._grace_timers.pop(app_id, None)
        pid = self._app_pid.get(app_id)
        if pid is None:
            return False
        log.info("auto-quit terminating", extra={"app_id": app_id, "pid": pid})
        self._terminator.terminate(pid)
        self._kill_timers[app_id] = self._scheduler.schedule(
            self._kill_timeout, lambda: self._force_kill(app_id, pid)
        )
        return False

    def _force_kill(self, app_id: str, pid: int) -> bool:
        self._kill_timers.pop(app_id, None)
        if self._terminator.is_alive(pid):
            log.warning("auto-quit force killing", extra={"app_id": app_id, "pid": pid})
            self._terminator.force_kill(pid)
        return False

    def _cancel_grace(self, app_id: str) -> None:
        handle = self._grace_timers.pop(app_id, None)
        if handle is not None:
            self._scheduler.cancel(handle)
