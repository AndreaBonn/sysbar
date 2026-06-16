"""System inhibitor adapter.

Holds a logind sleep/idle (or lid) inhibition via a file descriptor, plus a
freedesktop ScreenSaver inhibition to keep the display awake. Releasing closes
the descriptor and uninhibits the screensaver. This is boundary code (D-Bus),
exercised manually; the session logic that drives it is unit-tested separately.
"""

from __future__ import annotations

import contextlib
import logging
import os
from dataclasses import dataclass

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from .manager import WHAT_IDLE_SLEEP  # noqa: E402

log = logging.getLogger(__name__)

_LOGIND_NAME = "org.freedesktop.login1"
_LOGIND_PATH = "/org/freedesktop/login1"
_LOGIND_IFACE = "org.freedesktop.login1.Manager"
_SCREENSAVER_NAME = "org.freedesktop.ScreenSaver"
_SCREENSAVER_PATH = "/org/freedesktop/ScreenSaver"
_WHO = "Sysbar"
_WHY = "Keep awake"


@dataclass
class _Held:
    fd: int | None
    screensaver_cookie: int | None


class SystemInhibitor:
    """Acquire/release sleep, lid and screensaver inhibitions."""

    def __init__(self) -> None:
        self._system_bus: Gio.DBusConnection | None = None
        self._session_bus: Gio.DBusConnection | None = None

    def acquire(self, what: str) -> object | None:
        fd = self._logind_inhibit(what)
        cookie = self._screensaver_inhibit() if what == WHAT_IDLE_SLEEP else None
        if fd is None and cookie is None:
            log.warning("no inhibitor available", extra={"what": what})
            return None
        return _Held(fd=fd, screensaver_cookie=cookie)

    def release(self, token: object) -> None:
        if not isinstance(token, _Held):
            return
        if token.fd is not None:
            os.close(token.fd)
        if token.screensaver_cookie is not None:
            self._screensaver_uninhibit(token.screensaver_cookie)

    def _logind_inhibit(self, what: str) -> int | None:
        try:
            bus = self._get_system_bus()
            result, fd_list = bus.call_with_unix_fd_list_sync(
                _LOGIND_NAME,
                _LOGIND_PATH,
                _LOGIND_IFACE,
                "Inhibit",
                GLib.Variant("(ssss)", (what, _WHO, _WHY, "block")),
                GLib.VariantType("(h)"),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
                None,
            )
            return int(fd_list.get(result.unpack()[0]))
        except GLib.Error as error:
            log.warning("logind inhibit failed", extra={"what": what, "error": str(error)})
            return None

    def _screensaver_inhibit(self) -> int | None:
        try:
            bus = self._get_session_bus()
            result = bus.call_sync(
                _SCREENSAVER_NAME,
                _SCREENSAVER_PATH,
                _SCREENSAVER_NAME,
                "Inhibit",
                GLib.Variant("(ss)", (_WHO, _WHY)),
                GLib.VariantType("(u)"),
                Gio.DBusCallFlags.NONE,
                2000,
                None,
            )
            return int(result.unpack()[0])
        except GLib.Error:
            return None

    def _screensaver_uninhibit(self, cookie: int) -> None:
        with contextlib.suppress(GLib.Error):
            self._get_session_bus().call_sync(
                _SCREENSAVER_NAME,
                _SCREENSAVER_PATH,
                _SCREENSAVER_NAME,
                "UnInhibit",
                GLib.Variant("(u)", (cookie,)),
                None,
                Gio.DBusCallFlags.NONE,
                2000,
                None,
            )

    def _get_system_bus(self) -> Gio.DBusConnection:
        if self._system_bus is None:
            self._system_bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        return self._system_bus

    def _get_session_bus(self) -> Gio.DBusConnection:
        if self._session_bus is None:
            self._session_bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        return self._session_bus
