"""com.canonical.dbusmenu server backed by a :class:`MenuModel`.

Exporting the menu over D-Bus (rather than via a GTK3 ``Gtk.Menu``) is what
lets a GTK4 application drive an AppIndicator/StatusNotifierItem tray without
loading two incompatible GTK versions in the same process.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from .menu_model import ROOT_ID, MenuModel  # noqa: E402

if TYPE_CHECKING:
    from .menu_model import MenuItem

log = logging.getLogger(__name__)

DBUSMENU_IFACE = "com.canonical.dbusmenu"
_RECURSE_ALL = -1
_EVENT_CLICKED = "clicked"

_INTROSPECTION = """
<node>
  <interface name="com.canonical.dbusmenu">
    <method name="GetLayout">
      <arg type="i" name="parentId" direction="in"/>
      <arg type="i" name="recursionDepth" direction="in"/>
      <arg type="as" name="propertyNames" direction="in"/>
      <arg type="u" name="revision" direction="out"/>
      <arg type="(ia{sv}av)" name="layout" direction="out"/>
    </method>
    <method name="GetGroupProperties">
      <arg type="ai" name="ids" direction="in"/>
      <arg type="as" name="propertyNames" direction="in"/>
      <arg type="a(ia{sv})" name="properties" direction="out"/>
    </method>
    <method name="GetProperty">
      <arg type="i" name="id" direction="in"/>
      <arg type="s" name="name" direction="in"/>
      <arg type="v" name="value" direction="out"/>
    </method>
    <method name="Event">
      <arg type="i" name="id" direction="in"/>
      <arg type="s" name="eventId" direction="in"/>
      <arg type="v" name="data" direction="in"/>
      <arg type="u" name="timestamp" direction="in"/>
    </method>
    <method name="AboutToShow">
      <arg type="i" name="id" direction="in"/>
      <arg type="b" name="needUpdate" direction="out"/>
    </method>
    <property name="Version" type="u" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="TextDirection" type="s" access="read"/>
    <signal name="LayoutUpdated">
      <arg type="u" name="revision"/>
      <arg type="i" name="parent"/>
    </signal>
    <signal name="ItemsPropertiesUpdated">
      <arg type="a(ia{sv})" name="updatedProps"/>
      <arg type="a(ias)" name="removedProps"/>
    </signal>
  </interface>
</node>
"""


def _to_variant(value: object) -> GLib.Variant:
    if isinstance(value, bool):
        return GLib.Variant("b", value)
    if isinstance(value, int):
        return GLib.Variant("i", value)
    return GLib.Variant("s", str(value))


class DBusMenuServer:
    """Serve a :class:`MenuModel` on the ``com.canonical.dbusmenu`` interface."""

    def __init__(
        self, object_path: str, on_about_to_show: Callable[[], bool] | None = None
    ) -> None:
        self._object_path = object_path
        self._on_about_to_show = on_about_to_show
        self._model = MenuModel([])
        self._revision = 0
        self._connection: Gio.DBusConnection | None = None
        self._registration_id = 0
        node = Gio.DBusNodeInfo.new_for_xml(_INTROSPECTION)
        self._interface = node.lookup_interface(DBUSMENU_IFACE)

    def set_model(self, model: MenuModel) -> None:
        """Replace the menu and notify subscribers of the change.

        The shape is stable across updates (only labels, visibility and toggle
        state change), so a ``LayoutUpdated`` alone leaves many hosts showing the
        previous labels: they refresh item properties from
        ``ItemsPropertiesUpdated``, not by re-fetching the layout. Emitting both
        keeps dynamic labels (e.g. "Mute" vs "Unmute") in sync everywhere.
        """
        self._model = model
        self._revision += 1
        if self._connection is not None:
            self._emit_layout_updated()
            self._emit_items_properties_updated()

    def register(self, connection: Gio.DBusConnection) -> None:
        self._connection = connection
        self._registration_id = connection.register_object(
            self._object_path,
            self._interface,
            self._handle_method,
            None,
            None,
        )

    def unregister(self) -> None:
        if self._connection is not None and self._registration_id:
            self._connection.unregister_object(self._registration_id)
            self._registration_id = 0

    def _handle_method(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _path: str,
        _iface: str,
        method: str,
        params: GLib.Variant,
        invocation: Gio.DBusMethodInvocation,
    ) -> None:
        if method == "GetLayout":
            invocation.return_value(self._get_layout(*params.unpack()))
        elif method == "GetGroupProperties":
            invocation.return_value(self._get_group_properties(*params.unpack()))
        elif method == "GetProperty":
            invocation.return_value(self._get_property(*params.unpack()))
        elif method == "Event":
            self._on_event(*params.unpack())
            invocation.return_value(None)
        elif method == "AboutToShow":
            (item_id,) = params.unpack()
            invocation.return_value(GLib.Variant("(b)", (self._handle_about_to_show(item_id),)))
        else:
            invocation.return_error_literal(
                Gio.dbus_error_quark(), Gio.DBusError.UNKNOWN_METHOD, method
            )

    def _handle_about_to_show(self, item_id: int) -> bool:
        """Let the app refresh live menu values before the host re-reads the layout.

        Returning ``True`` tells the host the layout must be re-fetched before it
        is displayed, which is how dropdown metrics stay current without polling.

        Only the root popup triggers a refresh. A submenu open also fires
        ``AboutToShow`` (with the submenu's id); refreshing there rebuilds the
        whole menu and emits ``LayoutUpdated`` for the root, which cancels the
        host's in-progress submenu open so it never expands. Submenu contents
        stay current through ``ItemsPropertiesUpdated`` instead.
        """
        if item_id != ROOT_ID:
            return False
        if self._on_about_to_show is None:
            return False
        return bool(self._on_about_to_show())

    def _get_layout(self, parent_id: int, depth: int, names: list[str]) -> GLib.Variant:
        parent = self._model.get(parent_id) or self._model.root
        layout = self._build_item(parent, depth, names)
        return GLib.Variant("(u(ia{sv}av))", (self._revision, layout))

    def _build_item(
        self, item: MenuItem, depth: int, names: list[str]
    ) -> tuple[int, dict[str, GLib.Variant], list[GLib.Variant]]:
        # Returns a plain (id, props, children) tuple; GLib builds the struct.
        # The 'av' children, however, must be pre-boxed GLib.Variant values.
        props = self._props_variant(item, names)
        children: list[GLib.Variant] = []
        if depth != 0:
            child_depth = depth if depth == _RECURSE_ALL else depth - 1
            # Always emit every child, even hidden ones: dropping them would
            # change the node count and shift ids, desynchronising the host's
            # per-id cache. Visibility is carried by the "visible" property so
            # the host hides the row while ids stay stable across updates.
            for child in item.children:
                child_layout = self._build_item(child, child_depth, names)
                children.append(GLib.Variant("(ia{sv}av)", child_layout))
        return (item.item_id, props, children)

    def _props_variant(self, item: MenuItem, names: list[str]) -> dict[str, GLib.Variant]:
        props = self._model.properties(item)
        return {
            key: _to_variant(value) for key, value in props.items() if not names or key in names
        }

    def _get_group_properties(self, ids: list[int], names: list[str]) -> GLib.Variant:
        entries = []
        for item_id in ids:
            item = self._model.get(item_id)
            if item is not None:
                entries.append((item_id, self._props_variant(item, names)))
        return GLib.Variant("(a(ia{sv}))", (entries,))

    def _get_property(self, item_id: int, name: str) -> GLib.Variant:
        item = self._model.get(item_id)
        props = self._model.properties(item) if item is not None else {}
        value = props.get(name, "")
        return GLib.Variant("(v)", (_to_variant(value),))

    def _on_event(self, item_id: int, event_id: str, _data: object, _ts: int) -> None:
        if event_id != _EVENT_CLICKED:
            return
        action = self._model.action_for(item_id)
        if action is not None:
            GLib.idle_add(self._invoke, action)

    @staticmethod
    def _invoke(action: object) -> bool:
        if callable(action):
            action()
        return False

    def _emit_layout_updated(self) -> None:
        assert self._connection is not None
        self._connection.emit_signal(
            None,
            self._object_path,
            DBUSMENU_IFACE,
            "LayoutUpdated",
            GLib.Variant("(ui)", (self._revision, 0)),
        )

    def _properties_payload(self) -> list[tuple[int, dict[str, GLib.Variant]]]:
        """The (id, properties) pairs for every real item, for a push update."""
        return [(item.item_id, self._props_variant(item, [])) for item in self._model.all_items()]

    def _emit_items_properties_updated(self) -> None:
        assert self._connection is not None
        self._connection.emit_signal(
            None,
            self._object_path,
            DBUSMENU_IFACE,
            "ItemsPropertiesUpdated",
            GLib.Variant("(a(ia{sv})a(ias))", (self._properties_payload(), [])),
        )
