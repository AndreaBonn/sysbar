"""Floating shelf window with drag-in / drag-out tiles.

Boundary code: wires GTK4 drag-and-drop to the shelf service. The window is
undecorated and kept above where the window manager allows it.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk  # noqa: E402

from ...core.i18n import _  # noqa: E402
from ...services.shelf.models import ItemKind, ShelfItem  # noqa: E402
from ...services.shelf.pending_clear import PendingClear  # noqa: E402
from ...services.shelf.shelf_service import ShelfService  # noqa: E402

log = logging.getLogger(__name__)

_KIND_ICONS = {
    ItemKind.FILE: "text-x-generic-symbolic",
    ItemKind.IMAGE: "image-x-generic-symbolic",
    ItemKind.URL: "web-browser-symbolic",
    ItemKind.TEXT: "text-x-generic-symbolic",
}
_SHELF_WIDTH = 420
_SHELF_HEIGHT = 240
_TILE_WIDTH = 104
_TILE_HEIGHT = 112
_PREVIEW_WIDTH = 80
_PREVIEW_HEIGHT = 56
_ICON_PIXELS = 40
_UNDO_SECONDS = 5


class ShelfWindow(Adw.Window):
    """A floating tray of dropped files, images, text and links."""

    def __init__(self, service: ShelfService) -> None:
        super().__init__(title=_("Shelf"), decorated=False)
        self.set_default_size(_SHELF_WIDTH, _SHELF_HEIGHT)
        self._service = service
        self._flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, min_children_per_line=1)
        self._stack = Gtk.Stack()
        self._toasts = Adw.ToastOverlay()
        self._pending = PendingClear(service=service)
        self.connect("close-request", self._on_close_request)
        self._build_ui()
        self._setup_drop_target()
        service.connect("items-changed", lambda _s: self._rebuild_tiles())
        self._rebuild_tiles()

    def _build_ui(self) -> None:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        # S5: a word, not a bare bin icon whose meaning sits in a tooltip.
        clear = Gtk.Button(label=_("Clear"), tooltip_text=_("Clear shelf"))
        clear.connect("clicked", self._on_clear)
        header.pack_end(clear)
        toolbar.add_top_bar(header)

        for margin in ("top", "bottom", "start", "end"):
            getattr(self._flow, f"set_margin_{margin}")(8)
        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(self._flow)
        self._stack.add_named(scroller, "tiles")
        self._stack.add_named(_drop_hint(), "empty")
        self._toasts.set_child(self._stack)
        toolbar.set_content(self._toasts)
        self.set_content(toolbar)

    def _on_clear(self, _button: Gtk.Button) -> None:
        """S2: the clear is held for a few seconds so it can be undone."""
        batch = self._pending.clear()
        if batch is None:
            return
        toast = Adw.Toast(title=_("Shelf cleared"), button_label=_("Undo"), timeout=_UNDO_SECONDS)
        toast.connect("button-clicked", lambda _toast: self._pending.undo(batch=batch))
        toast.connect("dismissed", lambda _toast: self._pending.commit(batch=batch))
        self._toasts.add_toast(toast)

    def _on_close_request(self, _window: Gtk.Window) -> bool:
        self._pending.commit()
        return False

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
            self._service.add_dropped_text(value=value)
            return True
        return False

    def _rebuild_tiles(self) -> None:
        child = self._flow.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._flow.remove(child)
            child = nxt
        items = self._service.items
        for item in items:
            self._flow.append(self._make_tile(item))
        self._stack.set_visible_child_name("tiles" if items else "empty")

    def _make_tile(self, item: ShelfItem) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_size_request(_TILE_WIDTH, _TILE_HEIGHT)
        box.append(_preview(item))
        # M2: the full name is one hover away when the label is cut.
        label = Gtk.Label(
            label=item.label, ellipsize=3, max_width_chars=12, tooltip_text=item.label
        )
        box.append(label)

        remove = Gtk.Button(icon_name="window-close-symbolic", has_frame=False)
        remove.connect("clicked", lambda _b, item_id=item.id: self._service.remove(item_id))
        box.append(remove)

        source = Gtk.DragSource(actions=Gdk.DragAction.COPY)
        source.connect("prepare", self._make_prepare(item))
        box.add_controller(source)

        if item.open_uri is not None:
            box.set_tooltip_text(_("Double-click to open"))
            click = Gtk.GestureClick()
            # Capture phase so the double-click is seen before the DragSource
            # (bubble phase) can claim the sequence and cancel the gesture.
            click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            click.connect("released", self._make_open_handler(item))
            box.add_controller(click)
        return box

    def _make_open_handler(
        self, item: ShelfItem
    ) -> Callable[[Gtk.GestureClick, int, float, float], None]:
        def on_released(_gesture: Gtk.GestureClick, n_press: int, _x: float, _y: float) -> None:
            if n_press == 2:
                self._open_item(item)

        return on_released

    def _open_item(self, item: ShelfItem) -> None:
        if item.kind in (ItemKind.FILE, ItemKind.IMAGE) and item.path:
            file = Gio.File.new_for_path(item.path)
            Gtk.FileLauncher(file=file).launch(self, None, self._on_launch_done)
        elif item.kind is ItemKind.URL and item.text:
            Gtk.UriLauncher(uri=item.text).launch(self, None, self._on_launch_done)

    def _on_launch_done(
        self, launcher: Gtk.FileLauncher | Gtk.UriLauncher, result: Gio.AsyncResult
    ) -> None:
        try:
            launcher.launch_finish(result)
        except GLib.Error as error:
            log.warning("could not open shelf item: %s", error.message)

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


def _preview(item: ShelfItem) -> Gtk.Widget:
    """M2: an image shows itself; anything else gets a large kind icon."""
    if item.kind is ItemKind.IMAGE and item.path:
        # Gtk.Image scales a file to pixel_size; Gtk.Picture would grow to the
        # image's natural size and swallow the window.
        thumbnail = Gtk.Image.new_from_file(item.path)
        thumbnail.set_pixel_size(_PREVIEW_HEIGHT)
        thumbnail.set_size_request(_PREVIEW_WIDTH, _PREVIEW_HEIGHT)
        return thumbnail
    icon = Gtk.Image.new_from_icon_name(_KIND_ICONS[item.kind])
    icon.set_pixel_size(_ICON_PIXELS)
    icon.set_size_request(_PREVIEW_WIDTH, _PREVIEW_HEIGHT)
    return icon


def _drop_hint() -> Gtk.Widget:
    """M1: an empty shelf says how it is used."""
    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=6,
        valign=Gtk.Align.CENTER,
        css_classes=["card"],
        margin_top=12,
        margin_bottom=12,
        margin_start=12,
        margin_end=12,
    )
    title = Gtk.Label(label=_("Drop files, links or text here"), css_classes=["heading"])
    title.set_margin_top(16)
    hint = Gtk.Label(
        label=_("Keep them at hand while you switch windows. Double-click an item to open it."),
        css_classes=["dim-label"],
        wrap=True,
        justify=Gtk.Justification.CENTER,
    )
    hint.set_margin_bottom(16)
    hint.set_margin_start(12)
    hint.set_margin_end(12)
    box.append(title)
    box.append(hint)
    return box
