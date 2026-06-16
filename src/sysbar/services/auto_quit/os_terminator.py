"""Process terminator using POSIX signals."""

from __future__ import annotations

import logging
import os
import signal

log = logging.getLogger(__name__)


class OsTerminator:
    """Send SIGTERM/SIGKILL and probe liveness via ``os.kill``."""

    def terminate(self, pid: int) -> None:
        self._signal(pid, signal.SIGTERM)

    def force_kill(self, pid: int) -> None:
        self._signal(pid, signal.SIGKILL)

    def is_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    @staticmethod
    def _signal(pid: int, sig: signal.Signals) -> None:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass
        except PermissionError:
            log.warning("not permitted to signal process", extra={"pid": pid})
