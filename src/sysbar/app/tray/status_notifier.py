"""org.kde.StatusNotifierItem server.

Implements the StatusNotifierItem D-Bus interface (plus the Ayatana label
extension used by the GNOME AppIndicator host) and registers the item with the
StatusNotifierWatcher. No GTK widgets are involved.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

log = logging.getLogger(__name__)

SNI_IFACE = "org.kde.StatusNotifierItem"
SNI_OBJECT_PATH = "/StatusNotifierItem"
MENU_OBJECT_PATH = "/StatusNotifierItem/Menu"
WATCHER_NAME = "org.kde.StatusNotifierWatcher"
WATCHER_PATH = "/StatusNotifierWatcher"

_INTROSPECTION = """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <method name="Activate">
      <arg type="i" name="x" direction="in"/>
      <arg type="i" name="y" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <arg type="i" name="x" direction="in"/>
      <arg type="i" name="y" direction="in"/>
    </method>
    <method name="ContextMenu">
      <arg type="i" name="x" direction="in"/>
      <arg type="i" name="y" direction="in"/>
    </method>
    <method name="Scroll">
      <arg type="i" name="delta" direction="in"/>
      <arg type="s" name="orientation" direction="in"/>
    </method>
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <property name="XAyatanaLabel" type="s" access="read"/>
    <property name="XAyatanaLabelGuide" type="s" access="read"/>
    <signal name="NewIcon"/>
    <signal name="NewTitle"/>
    <signal name="NewStatus"><arg type="s" name="status"/></signal>
    <signal name="XAyatanaNewLabel">
      <arg type="s" name="label"/>
      <arg type="s" name="guide"/>
    </signal>
  </interface>
</node>
"""


class StatusNotifierItem:
    """Serve and register a StatusNotifierItem on the session bus."""

    def __init__(self, title: str, icon_name: str, on_activate: Callable[[], None]) -> None:
        self._title = title
        self._icon_name = icon_name
        self._label = ""
        self._on_activate = on_activate
        self._connection: Gio.DBusConnection | None = None
        self._registration_id = 0
        node = Gio.DBusNodeInfo.new_for_xml(_INTROSPECTION)
        self._interface = node.lookup_interface(SNI_IFACE)

    def register(self, connection: Gio.DBusConnection) -> None:
        """Export the item and register it with the StatusNotifierWatcher."""
        self._connection = connection
        self._registration_id = connection.register_object(
            SNI_OBJECT_PATH,
            self._interface,
            self._handle_method,
            self._get_property,
            None,
        )
        self._register_with_watcher(connection)

    def unregister(self) -> None:
        if self._connection is not None and self._registration_id:
            self._connection.unregister_object(self._registration_id)
            self._registration_id = 0

    def set_label(self, label: str) -> None:
        """Set the text shown next to the icon (Ayatana extension)."""
        if label == self._label:
            return
        self._label = label
        if self._connection is not None:
            self._connection.emit_signal(
                None,
                SNI_OBJECT_PATH,
                SNI_IFACE,
                "XAyatanaNewLabel",
                GLib.Variant("(ss)", (label, "")),
            )

    def set_icon(self, icon_name: str) -> None:
        if icon_name == self._icon_name:
            return
        self._icon_name = icon_name
        if self._connection is not None:
            self._connection.emit_signal(None, SNI_OBJECT_PATH, SNI_IFACE, "NewIcon", None)

    def _register_with_watcher(self, connection: Gio.DBusConnection) -> None:
        try:
            connection.call_sync(
                WATCHER_NAME,
                WATCHER_PATH,
                WATCHER_NAME,
                "RegisterStatusNotifierItem",
                GLib.Variant("(s)", (connection.get_unique_name(),)),
                None,
                Gio.DBusCallFlags.NONE,
                2000,
                None,
            )
        except GLib.Error as error:
            log.warning("StatusNotifierWatcher unavailable", extra={"error": str(error)})

    def _handle_method(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _path: str,
        _iface: str,
        method: str,
        _params: GLib.Variant,
        invocation: Gio.DBusMethodInvocation,
    ) -> None:
        if method in ("Activate", "SecondaryActivate"):
            GLib.idle_add(self._activate)
        invocation.return_value(None)

    def _activate(self) -> bool:
        self._on_activate()
        return False

    def _get_property(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _path: str,
        _iface: str,
        name: str,
    ) -> GLib.Variant | None:
        values: dict[str, GLib.Variant] = {
            "Category": GLib.Variant("s", "SystemServices"),
            "Id": GLib.Variant("s", "sysbar"),
            "Title": GLib.Variant("s", self._title),
            "Status": GLib.Variant("s", "Active"),
            "IconName": GLib.Variant("s", self._icon_name),
            "ItemIsMenu": GLib.Variant("b", False),
            "Menu": GLib.Variant("o", MENU_OBJECT_PATH),
            "XAyatanaLabel": GLib.Variant("s", self._label),
            "XAyatanaLabelGuide": GLib.Variant("s", ""),
        }
        return values.get(name)
