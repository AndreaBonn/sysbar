"""Floating shelf window with drag-in / drag-out tiles.

Boundary code: wires GTK4 drag-and-drop to the shelf service. The window is
undecorated and kept above where the window manager allows it.
"""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk  # noqa: E402

from ...services.shelf.models import ItemKind, ShelfItem  # noqa: E402
from ...services.shelf.shelf_service import ShelfService  # noqa: E402

_URL_SCHEMES = ("http://", "https://", "ftp://")
_KIND_ICONS = {
    ItemKind.FILE: "text-x-generic-symbolic",
    ItemKind.IMAGE: "image-x-generic-symbolic",
    ItemKind.URL: "web-browser-symbolic",
    ItemKind.TEXT: "text-x-generic-symbolic",
}
_SHELF_WIDTH = 420
_SHELF_HEIGHT = 220


class ShelfWindow(Adw.Window):
    """A floating tray of dropped files, images, text and links."""

    def __init__(self, service: ShelfService) -> None:
        super().__init__(title="Shelf", decorated=False)
        self.set_default_size(_SHELF_WIDTH, _SHELF_HEIGHT)
        self._service = service
        self._flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, min_children_per_line=1)
        self._build_ui()
        self._setup_drop_target()
        service.connect("items-changed", lambda _s: self._rebuild_tiles())
        self._rebuild_tiles()

    def _build_ui(self) -> None:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        clear = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Clear shelf")
        clear.connect("clicked", lambda _b: self._service.clear())
        header.pack_end(clear)
        toolbar.add_top_bar(header)

        self._flow.set_margin_top(8)
        self._flow.set_margin_bottom(8)
        self._flow.set_margin_start(8)
        self._flow.set_margin_end(8)
        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(self._flow)
        toolbar.set_content(scroller)
        self.set_content(toolbar)

    def _setup_drop_target(self) -> None:
        drop = Gtk.DropTarget.new(GObject.TYPE_NONE, Gdk.DragAction.COPY)
        drop.set_gtypes([Gdk.FileList, Gdk.Texture, str])
        drop.connect("drop", self._on_drop)
        self.add_controller(drop)

    def _on_drop(self, _target: Gtk.DropTarget, value: object, _x: float, _y: float) -> bool:
        if isinstance(value, Gdk.FileList):
            for file in value.get_files():
                path = file.get_path()
                if path:
                    self._service.add_file(path)
            return True
        if isinstance(value, Gdk.Texture):
            self._service.add_image(bytes(value.save_to_png_bytes().get_data()))
            return True
        if isinstance(value, str):
            self._add_text_or_url(value)
            return True
        return False

    def _add_text_or_url(self, value: str) -> None:
        if value.startswith(_URL_SCHEMES):
            self._service.add_url(value)
        else:
            self._service.add_text(value)

    def _rebuild_tiles(self) -> None:
        child = self._flow.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._flow.remove(child)
            child = nxt
        for item in self._service.items:
            self._flow.append(self._make_tile(item))

    def _make_tile(self, item: ShelfItem) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_size_request(96, 84)
        box.append(Gtk.Image.new_from_icon_name(_KIND_ICONS[item.kind]))
        label = Gtk.Label(label=item.label, ellipsize=3, max_width_chars=12)
        box.append(label)

        remove = Gtk.Button(icon_name="window-close-symbolic", has_frame=False)
        remove.connect("clicked", lambda _b, item_id=item.id: self._service.remove(item_id))
        box.append(remove)

        source = Gtk.DragSource(actions=Gdk.DragAction.COPY)
        source.connect("prepare", self._make_prepare(item))
        box.add_controller(source)
        return box

    def _make_prepare(
        self, item: ShelfItem
    ) -> Callable[[Gtk.DragSource, float, float], Gdk.ContentProvider | None]:
        def prepare(_source: Gtk.DragSource, _x: float, _y: float) -> Gdk.ContentProvider | None:
            if item.path:
                uri = Gio.File.new_for_path(item.path).get_uri()
                return Gdk.ContentProvider.new_for_bytes(
                    "text/uri-list", GLib.Bytes.new(f"{uri}\r\n".encode())
                )
            if item.text is not None:
                return Gdk.ContentProvider.new_for_value(item.text)
            return None

        return prepare
