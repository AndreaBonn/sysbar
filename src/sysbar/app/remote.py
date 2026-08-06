"""Invoking a command on the Sysbar instance that is already running.

The application exports its actions as ``org.gtk.Actions``, so the command line
does not need an IPC channel of its own: it calls the running process over the
session bus and exits.

Deliberately GTK-free. The CLI process only ever touches Gio, so ``sysbar
open-panel`` neither initialises a display nor risks the GTK3/GTK4 clash that
importing the UI would bring in through libwnck.

Starting the application is not this module's job either. A command line that
silently spawned a tray daemon would be a surprising thing to put in a script,
so an instance that is not running is an error with a message.
"""

from __future__ import annotations

from typing import Protocol

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from ..core.constants import APP_ID, DBUS_OBJECT_PATH  # noqa: E402

_ACTIONS_INTERFACE = "org.gtk.Actions"
_ACTIVATE_METHOD = "Activate"
_DBUS_NAME = "org.freedesktop.DBus"
_DBUS_PATH = "/org/freedesktop/DBus"
_DBUS_INTERFACE = "org.freedesktop.DBus"
_NAME_HAS_OWNER = "NameHasOwner"
_CALL_TIMEOUT_MS = 5000

OBJECT_PATH = DBUS_OBJECT_PATH


class NotRunningError(RuntimeError):
    """Raised when no Sysbar instance owns the bus name."""


class RemoteControl(Protocol):
    """Invoking a command on a running instance."""

    def is_running(self) -> bool: ...

    def activate(self, command: str, argument: str | None = None) -> None: ...


class DBusRemoteControl:
    """Talks to the running instance over the session bus."""

    def __init__(self, bus: Gio.DBusConnection | None = None) -> None:
        self._bus = bus or Gio.bus_get_sync(Gio.BusType.SESSION, None)

    def is_running(self) -> bool:
        """Whether any process currently owns the Sysbar bus name."""
        reply = self._bus.call_sync(
            _DBUS_NAME,
            _DBUS_PATH,
            _DBUS_INTERFACE,
            _NAME_HAS_OWNER,
            GLib.Variant("(s)", (APP_ID,)),
            GLib.VariantType.new("(b)"),
            Gio.DBusCallFlags.NONE,
            _CALL_TIMEOUT_MS,
            None,
        )
        return bool(reply.unpack()[0])

    def activate(self, command: str, argument: str | None = None) -> None:
        """Activate ``command`` on the running instance.

        Raises
        ------
        NotRunningError
            If no instance owns the bus name.
        """
        if not self.is_running():
            raise NotRunningError(APP_ID)
        arguments = [GLib.Variant("s", argument)] if argument is not None else []
        try:
            self._bus.call_sync(
                APP_ID,
                OBJECT_PATH,
                _ACTIONS_INTERFACE,
                _ACTIVATE_METHOD,
                GLib.Variant("(sava{sv})", (command, arguments, {})),
                None,
                Gio.DBusCallFlags.NONE,
                _CALL_TIMEOUT_MS,
                None,
            )
        except GLib.Error as error:
            # The instance can quit between the ownership check and the call.
            # Report that as "not running" rather than leaking a bus error: from
            # the caller's side the two are the same situation.
            if not self.is_running():
                raise NotRunningError(APP_ID) from error
            raise
