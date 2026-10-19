"""System inhibitor adapter.

Provides logind file-descriptor and freedesktop ScreenSaver cookie adapters.
Composition and partial-success decisions live in the pure combined inhibitor.
This is boundary code (D-Bus),
exercised manually; the session logic that drives it is unit-tested separately.
"""

from __future__ import annotations

import contextlib
import logging
import os

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

log = logging.getLogger(__name__)

_LOGIND_NAME = "org.freedesktop.login1"
_LOGIND_PATH = "/org/freedesktop/login1"
_LOGIND_IFACE = "org.freedesktop.login1.Manager"
_SCREENSAVER_NAME = "org.freedesktop.ScreenSaver"
_SCREENSAVER_PATH = "/org/freedesktop/ScreenSaver"
_WHO = "Sysbar"
_WHY = "Keep awake"


class LogindSleepInhibitor:
    """Hold logind inhibitions through Unix file descriptors."""

    def __init__(self) -> None:
        self._system_bus: Gio.DBusConnection | None = None

    def release(self, fd: int) -> None:
        os.close(fd)

    def acquire(self, what: str) -> int | None:
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

    def _get_system_bus(self) -> Gio.DBusConnection:
        if self._system_bus is None:
            self._system_bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        return self._system_bus


class ScreenSaverInhibitor:
    """Hold display inhibitions through ScreenSaver cookies."""

    def __init__(self) -> None:
        self._session_bus: Gio.DBusConnection | None = None

    def acquire(self) -> int | None:
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
        except GLib.Error as error:
            log.warning("screensaver inhibit failed", extra={"error": str(error)})
            return None

    def release(self, cookie: int) -> None:
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

    def _get_session_bus(self) -> Gio.DBusConnection:
        if self._session_bus is None:
            self._session_bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        return self._session_bus
