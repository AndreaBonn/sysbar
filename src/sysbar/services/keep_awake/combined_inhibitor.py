"""Compose partial inhibition successes outside the D-Bus adapters and feature."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .ports import WHAT_IDLE_SLEEP, ScreenSaverInhibitor, SleepInhibitor

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Held:
    fd: int | None
    screensaver_cookie: int | None


class CombinedInhibitor:
    """Acquire/release sleep, lid and screensaver inhibitions."""

    def __init__(self, sleep: SleepInhibitor, screensaver: ScreenSaverInhibitor) -> None:
        self._sleep = sleep
        self._screensaver = screensaver

    def acquire(self, what: str) -> object | None:
        fd = self._sleep.acquire(what)
        cookie = self._screensaver.acquire() if what == WHAT_IDLE_SLEEP else None
        if fd is None and cookie is None:
            log.warning("no inhibitor available", extra={"what": what})
            return None
        return _Held(fd=fd, screensaver_cookie=cookie)

    def release(self, token: object) -> None:
        if not isinstance(token, _Held):
            return
        if token.fd is not None:
            self._sleep.release(fd=token.fd)
        if token.screensaver_cookie is not None:
            self._screensaver.release(cookie=token.screensaver_cookie)
