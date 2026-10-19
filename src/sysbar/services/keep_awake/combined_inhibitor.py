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
    """Hold a logind inhibition and a ScreenSaver one as a single token.

    logind keeps the machine from sleeping (or the lid from suspending it);
    the ScreenSaver inhibition keeps the display awake, so it is taken only
    for an idle:sleep session. Either part may fail on its own: the token
    holds whatever was acquired, and is None only when neither was.
    """

    def __init__(self, sleep: SleepInhibitor, screensaver: ScreenSaverInhibitor) -> None:
        self._sleep = sleep
        self._screensaver = screensaver

    def acquire(self, what: str) -> object | None:
        fd = self._sleep.acquire(what)
        cookie = self._screensaver.acquire() if what == WHAT_IDLE_SLEEP else None
        if fd is None and cookie is None:
            log.warning("no inhibitor available", extra={"what": what})
            return None
        missing = _missing_part(what=what, fd=fd, cookie=cookie)
        if missing is not None:
            # The token is valid, so keep-awake reads as on although only half of it holds.
            log.warning("partial inhibition", extra={"what": what, "missing": missing})
        return _Held(fd=fd, screensaver_cookie=cookie)

    def release(self, token: object) -> None:
        if not isinstance(token, _Held):
            return
        if token.fd is not None:
            self._sleep.release(fd=token.fd)
        if token.screensaver_cookie is not None:
            self._screensaver.release(cookie=token.screensaver_cookie)


def _missing_part(*, what: str, fd: int | None, cookie: int | None) -> str | None:
    """Which half of an idle:sleep inhibition failed, if exactly one did."""
    if what != WHAT_IDLE_SLEEP:
        return None
    if fd is None:
        return "sleep"
    if cookie is None:
        return "screensaver"
    return None
