"""Clipboard history window: search, pin, re-copy and delete entries.

A search box filters the list live; activating a row copies it back to the
clipboard, and each row can be pinned (protected from eviction) or removed.
"""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ...core.i18n import _  # noqa: E402
from ...services.clipboard.models import ClipEntry  # noqa: E402
from ...services.clipboard.service import ClipboardService  # noqa: E402
from ..footer import build_footer  # noqa: E402

CopyCallback = Callable[[str], None]

_WINDOW_WIDTH = 420
_WINDOW_HEIGHT = 560
_PINNED_ICON = "starred-symbolic"
_UNPINNED_ICON = "non-starred-symbolic"


class ClipboardWindow(Adw.Window):
    """Browsable, searchable clipboard history."""

    def __init__(self, service: ClipboardService, on_copy: CopyCallback) -> None:
        super().__init__(title=_("Clipboard"))
        self.set_default_size(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self._service = service
        self._on_copy = on_copy
        self._group = Adw.PreferencesGroup()
        self._rows: list[Adw.ActionRow] = []
        self._search = Gtk.SearchEntry(placeholder_text=_("Search clipboard"))
        self._build_content()
        self._search.connect("search-changed", lambda _e: self._rebuild())
        self._service.connect("items-changed", lambda _s: self._rebuild())
        self._rebuild()

    def _build_content(self) -> None:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        clear = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text=_("Clear unpinned"))
        clear.connect("clicked", lambda _b: self._service.clear())
        header.pack_end(clear)
        toolbar.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for margin in ("top", "bottom", "start", "end"):
            getattr(content, f"set_margin_{margin}")(12)
        content.append(self._search)

        page = Adw.PreferencesPage()
        page.add(self._group)
        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(page)
        content.append(scroller)

        toolbar.set_content(content)
        toolbar.add_bottom_bar(build_footer())
        self.set_content(toolbar)

    def _rebuild(self) -> None:
        for row in self._rows:
            self._group.remove(row)
        self._rows.clear()
        for entry in self._service.search(self._search.get_text()):
            row = self._build_row(entry)
            self._group.add(row)
            self._rows.append(row)

    def _build_row(self, entry: ClipEntry) -> Adw.ActionRow:
        row = Adw.ActionRow(title=entry.label, subtitle=entry.kind.value, activatable=True)
        row.connect("activated", lambda _r, text=entry.text: self._on_copy(text))

        pin = Gtk.Button(
            icon_name=_PINNED_ICON if entry.pinned else _UNPINNED_ICON,
            tooltip_text=_("Unpin") if entry.pinned else _("Pin"),
            valign=Gtk.Align.CENTER,
        )
        pin.add_css_class("flat")
        pin.connect("clicked", lambda _b, eid=entry.id: self._service.toggle_pin(eid))
        row.add_suffix(pin)

        delete = Gtk.Button(
            icon_name="edit-delete-symbolic", tooltip_text=_("Remove"), valign=Gtk.Align.CENTER
        )
        delete.add_css_class("flat")
        delete.connect("clicked", lambda _b, eid=entry.id: self._service.remove(eid))
        row.add_suffix(delete)
        return row
