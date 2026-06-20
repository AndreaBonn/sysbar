"""xdg-desktop-portal GlobalShortcuts client (the system boundary).

Implements :class:`GlobalShortcuts` on top of
``org.freedesktop.portal.GlobalShortcuts``, which works on both X11 and Wayland.
The portal uses a request/response pattern: ``CreateSession`` returns a Request
object whose ``Response`` signal carries the real ``session_handle``; shortcuts
are then bound to that session and activations arrive as ``Activated`` signals.
This is boundary code exercised manually (a portal is required), so it carries
no unit tests; the binding decision lives in :class:`HotkeyManager`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

log = logging.getLogger(__name__)

_PORTAL_NAME = "org.freedesktop.portal.Desktop"
_PORTAL_PATH = "/org/freedesktop/portal/desktop"
_SHORTCUTS_IFACE = "org.freedesktop.portal.GlobalShortcuts"
_REQUEST_IFACE = "org.freedesktop.portal.Request"
_HANDLE_TOKEN = "sysbar_shortcuts"
_SESSION_TOKEN = "sysbar_session"
_RESPONSE_SUCCESS = 0


class PortalGlobalShortcuts:  # pragma: no cover - xdg-desktop-portal boundary
    """Registers global shortcuts through the desktop portal."""

    def __init__(self) -> None:
        self._callbacks: dict[str, Callable[[], None]] = {}
        self._pending: list[tuple[str, str]] = []
        self._session_handle: str | None = None
        self._session_requested = False
        self._proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            _PORTAL_NAME,
            _PORTAL_PATH,
            _SHORTCUTS_IFACE,
            None,
        )
        self._connection = self._proxy.get_connection()
        self._connection.signal_subscribe(
            _PORTAL_NAME,
            _SHORTCUTS_IFACE,
            "Activated",
            _PORTAL_PATH,
            None,
            Gio.DBusSignalFlags.NONE,
            self._on_activated,
        )

    def bind(self, shortcut_id: str, description: str, on_activated: Callable[[], None]) -> None:
        self._callbacks[shortcut_id] = on_activated
        self._pending.append((shortcut_id, description))
        if self._session_handle is not None:
            self._bind_pending()
        elif not self._session_requested:
            self._session_requested = True
            self._create_session()

    def _create_session(self) -> None:
        # The Request object path is deterministic from our unique name and the
        # handle token (portal spec), so we can subscribe to its Response before
        # the call returns and read the real session handle from there.
        unique = self._connection.get_unique_name().lstrip(":").replace(".", "_")
        request_path = f"{_PORTAL_PATH}/request/{unique}/{_HANDLE_TOKEN}"
        self._connection.signal_subscribe(
            _PORTAL_NAME,
            _REQUEST_IFACE,
            "Response",
            request_path,
            None,
            Gio.DBusSignalFlags.NONE,
            self._on_session_response,
        )
        options = {
            "handle_token": GLib.Variant("s", _HANDLE_TOKEN),
            "session_handle_token": GLib.Variant("s", _SESSION_TOKEN),
        }
        self._proxy.call_sync(
            "CreateSession",
            GLib.Variant("(a{sv})", (options,)),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )

    def _on_session_response(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _path: str,
        _iface: str,
        _signal: str,
        params: GLib.Variant,
    ) -> None:
        response_code, results = params.unpack()
        if response_code != _RESPONSE_SUCCESS or "session_handle" not in results:
            log.warning("global shortcuts session refused", extra={"code": response_code})
            return
        self._session_handle = results["session_handle"]
        self._bind_pending()

    def _bind_pending(self) -> None:
        if self._session_handle is None or not self._pending:
            return
        shortcuts = [
            (
                shortcut_id,
                {
                    "description": GLib.Variant("s", description),
                    "preferred_trigger": GLib.Variant("s", ""),
                },
            )
            for shortcut_id, description in self._pending
        ]
        self._pending.clear()
        self._proxy.call_sync(
            "BindShortcuts",
            GLib.Variant("(oa(sa{sv})sa{sv})", (self._session_handle, shortcuts, "", {})),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )

    def _on_activated(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _path: str,
        _iface: str,
        _signal: str,
        params: GLib.Variant,
    ) -> None:
        _session, shortcut_id, *_rest = params.unpack()
        callback = self._callbacks.get(shortcut_id)
        if callback is not None:
            callback()
