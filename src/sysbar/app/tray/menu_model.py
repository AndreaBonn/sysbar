"""Tray menu model.

A framework-agnostic description of the tray menu. The model assigns stable
integer ids (the com.canonical.dbusmenu protocol identifies items by id) and
maps an item to its activation callback. Serialization to D-Bus variants lives
in :mod:`sysbar.app.tray.dbus_menu`, keeping this module free of GI imports and
unit-testable.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

TYPE_STANDARD = "standard"
TYPE_SEPARATOR = "separator"
TOGGLE_NONE = -1
TOGGLE_OFF = 0
TOGGLE_ON = 1
ROOT_ID = 0


@dataclass
class MenuItem:
    """One tray menu entry."""

    label: str = ""
    item_type: str = TYPE_STANDARD
    enabled: bool = True
    visible: bool = True
    toggle_type: str = ""
    toggle_state: int = TOGGLE_NONE
    icon_name: str = ""
    action: Callable[[], None] | None = None
    children: list[MenuItem] = field(default_factory=list)
    item_id: int = -1


class MenuModel:
    """A tree of :class:`MenuItem` with stable ids and event dispatch."""

    def __init__(self, root_items: list[MenuItem]) -> None:
        self._root = MenuItem(label="root", children=root_items)
        self._by_id: dict[int, MenuItem] = {}
        self._assign_ids()

    def _assign_ids(self) -> None:
        self._by_id.clear()
        counter = ROOT_ID
        for item in self._walk(self._root):
            item.item_id = counter
            self._by_id[counter] = item
            counter += 1

    def _walk(self, item: MenuItem) -> Iterator[MenuItem]:
        yield item
        for child in item.children:
            yield from self._walk(child)

    @property
    def root(self) -> MenuItem:
        return self._root

    def get(self, item_id: int) -> MenuItem | None:
        return self._by_id.get(item_id)

    def properties(self, item: MenuItem) -> dict[str, object]:
        """Return the dbusmenu property map for an item (plain Python types)."""
        if item.item_type == TYPE_SEPARATOR:
            return {"type": TYPE_SEPARATOR, "visible": item.visible}
        props: dict[str, object] = {
            "label": item.label,
            "enabled": item.enabled,
            "visible": item.visible,
        }
        if item.icon_name:
            props["icon-name"] = item.icon_name
        if item.toggle_type:
            props["toggle-type"] = item.toggle_type
            props["toggle-state"] = item.toggle_state
        if item.children:
            props["children-display"] = "submenu"
        return props

    def action_for(self, item_id: int) -> Callable[[], None] | None:
        """Return the activation callback for an item id, if any."""
        item = self._by_id.get(item_id)
        return item.action if item is not None else None
