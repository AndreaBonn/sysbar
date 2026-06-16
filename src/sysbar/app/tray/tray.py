"""Tray facade: wires the StatusNotifierItem and its dbusmenu together."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio  # noqa: E402

from ...core.constants import TRAY_ICON_NAME, TRAY_TITLE  # noqa: E402
from .dbus_menu import DBusMenuServer  # noqa: E402
from .menu_model import MenuModel  # noqa: E402
from .status_notifier import MENU_OBJECT_PATH, StatusNotifierItem  # noqa: E402


class Tray:
    """High-level tray controller used by the application."""

    def __init__(self, on_activate: Callable[[], None]) -> None:
        self._sni = StatusNotifierItem(TRAY_TITLE, TRAY_ICON_NAME, on_activate)
        self._menu = DBusMenuServer(MENU_OBJECT_PATH)

    def register(self, connection: Gio.DBusConnection) -> None:
        """Export both objects and announce the item to the watcher."""
        self._menu.register(connection)
        self._sni.register(connection)

    def unregister(self) -> None:
        self._sni.unregister()
        self._menu.unregister()

    def set_menu(self, model: MenuModel) -> None:
        self._menu.set_model(model)

    def set_label(self, label: str) -> None:
        self._sni.set_label(label)

    def set_icon(self, icon_name: str) -> None:
        self._sni.set_icon(icon_name)
