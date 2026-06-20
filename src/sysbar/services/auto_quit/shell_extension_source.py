"""Wayland window source backed by the Sysbar GNOME Shell extension.

On Wayland there is no libwnck, so the extension (running inside gnome-shell)
exports window open/close events over D-Bus. This adapter implements the same
:class:`WindowSource` port as the X11 libwnck source, so ``AutoQuitService`` is
unchanged. Boundary code (D-Bus); the tracking logic it feeds is unit-tested.
"""

from __future__ import annotations

import logging

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from ...core.constants import (  # noqa: E402
    SHELL_EXTENSION_BUS_NAME,
    SHELL_EXTENSION_INTERFACE,
    SHELL_EXTENSION_OBJECT_PATH,
)
from .ports import WindowClosedCallback, WindowOpenedCallback  # noqa: E402

log = logging.getLogger(__name__)


class ShellExtensionWindowSource:  # pragma: no cover - D-Bus boundary (requires the extension)
    """Emits window events from the Sysbar GNOME Shell extension."""

    def __init__(self) -> None:
        self._on_opened: WindowOpenedCallback | None = None
        self._on_closed: WindowClosedCallback | None = None
        self._proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            SHELL_EXTENSION_BUS_NAME,
            SHELL_EXTENSION_OBJECT_PATH,
            SHELL_EXTENSION_INTERFACE,
            None,
        )

    def subscribe(self, on_opened: WindowOpenedCallback, on_closed: WindowClosedCallback) -> None:
        self._on_opened = on_opened
        self._on_closed = on_closed
        connection = self._proxy.get_connection()
        connection.signal_subscribe(
            SHELL_EXTENSION_BUS_NAME,
            SHELL_EXTENSION_INTERFACE,
            "WindowOpened",
            SHELL_EXTENSION_OBJECT_PATH,
            None,
            Gio.DBusSignalFlags.NONE,
            self._handle_opened,
        )
        connection.signal_subscribe(
            SHELL_EXTENSION_BUS_NAME,
            SHELL_EXTENSION_INTERFACE,
            "WindowClosed",
            SHELL_EXTENSION_OBJECT_PATH,
            None,
            Gio.DBusSignalFlags.NONE,
            self._handle_closed,
        )
        self._seed_existing_windows()

    def _seed_existing_windows(self) -> None:
        result = self._proxy.call_sync("ListWindows", None, Gio.DBusCallFlags.NONE, -1, None)
        for window_id, wm_class, pid in result.unpack()[0]:
            self._emit_opened(window_id, wm_class, pid)

    def _handle_opened(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _path: str,
        _iface: str,
        _signal: str,
        params: GLib.Variant,
    ) -> None:
        window_id, wm_class, pid = params.unpack()
        self._emit_opened(window_id, wm_class, pid)

    def _handle_closed(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _path: str,
        _iface: str,
        _signal: str,
        params: GLib.Variant,
    ) -> None:
        (window_id,) = params.unpack()
        if self._on_closed is not None:
            self._on_closed(int(window_id))

    def _emit_opened(self, window_id: int, wm_class: str, pid: int) -> None:
        if self._on_opened is not None:
            self._on_opened(int(window_id), wm_class or None, pid or None)
