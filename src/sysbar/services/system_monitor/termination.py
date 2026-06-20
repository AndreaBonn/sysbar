"""User-requested process termination.

Unlike auto-quit (which tracks windows), this service kills a single process on
demand from the panel: it sends SIGTERM, then escalates to SIGKILL after a grace
period if the process is still alive. The terminator and scheduler are injected,
reusing the same ports as auto-quit, so the escalation logic is unit-tested
without real signals or timers.
"""

from __future__ import annotations

import logging

from ...core.constants import PROCESS_KILL_TIMEOUT_SECONDS
from ..auto_quit.ports import Scheduler, Terminator

log = logging.getLogger(__name__)


class ProcessTerminationService:
    """Terminates a process by PID, escalating SIGTERM to SIGKILL."""

    def __init__(
        self,
        terminator: Terminator,
        scheduler: Scheduler,
        kill_timeout_seconds: float = PROCESS_KILL_TIMEOUT_SECONDS,
    ) -> None:
        self._terminator = terminator
        self._scheduler = scheduler
        self._kill_timeout = kill_timeout_seconds
        self._pending: dict[int, int] = {}

    def terminate(self, pid: int) -> None:
        """Send SIGTERM and schedule a SIGKILL fallback if the process survives."""
        log.info("user terminating process", extra={"pid": pid})
        self._terminator.terminate(pid)
        if pid in self._pending:
            return
        self._pending[pid] = self._scheduler.schedule(
            self._kill_timeout, lambda: self._force_kill(pid)
        )

    def _force_kill(self, pid: int) -> bool:
        self._pending.pop(pid, None)
        if self._terminator.is_alive(pid):
            log.warning("force killing process", extra={"pid": pid})
            self._terminator.force_kill(pid)
        return False
