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
from ...services.clipboard.models import ClipEntry, ClipKind  # noqa: E402
from ...services.clipboard.service import ClipboardService  # noqa: E402

CopyCallback = Callable[[str], None]

_WINDOW_WIDTH = 420
_WINDOW_HEIGHT = 560
_PINNED_ICON = "starred-symbolic"
_UNPINNED_ICON = "non-starred-symbolic"
# C2: the kind as an icon and a word, not the raw enum value.
_KIND_ICONS = {ClipKind.TEXT: "text-x-generic-symbolic", ClipKind.URL: "web-browser-symbolic"}
_KIND_LABELS = {ClipKind.TEXT: "Text", ClipKind.URL: "Link"}
_TOAST_SECONDS = 2
_UNDO_SECONDS = 5


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
        self._stack = Gtk.Stack()
        self._toasts = Adw.ToastOverlay()
        self._empty = Adw.StatusPage(icon_name="edit-paste-symbolic")
        self._build_content()
        self._search.connect("search-changed", lambda _e: self._rebuild())
        self._service.connect("items-changed", lambda _s: self._rebuild())
        self._rebuild()

    def _build_content(self) -> None:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        # S5: a word, not a bare bin icon whose meaning sits in a tooltip.
        clear = Gtk.Button(label=_("Clear"), tooltip_text=_("Clear unpinned"))
        clear.connect("clicked", self._on_clear)
        header.pack_end(clear)
        toolbar.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for margin in ("top", "bottom", "start", "end"):
            getattr(content, f"set_margin_{margin}")(12)
        content.append(self._search)

        self._group.set_description(_("Click an entry to copy it again."))
        page = Adw.PreferencesPage()
        page.add(self._group)
        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(page)
        self._stack.add_named(scroller, "list")
        self._stack.add_named(self._empty, "empty")
        content.append(self._stack)

        self._toasts.set_child(content)
        toolbar.set_content(self._toasts)
        self.set_content(toolbar)

    def _rebuild(self) -> None:
        for row in self._rows:
            self._group.remove(row)
        self._rows.clear()
        query = self._search.get_text()
        for entry in self._service.search(query):
            row = self._build_row(entry)
            self._group.add(row)
            self._rows.append(row)
        self._show_empty(query)

    def _show_empty(self, query: str) -> None:
        """C1: say how the history fills, or that the search found nothing."""
        if self._rows:
            self._stack.set_visible_child_name("list")
            return
        if query:
            self._empty.set_title(_("No entries match"))
            self._empty.set_description(_("Try fewer letters."))
        else:
            self._empty.set_title(_("Nothing copied yet"))
            self._empty.set_description(
                _("Copy some text or a link anywhere: it appears here, ready to copy again.")
            )
        self._stack.set_visible_child_name("empty")

    def _copy(self, text: str) -> None:
        """C3: copying back gets a confirmation, not silence."""
        self._on_copy(text)
        self._toasts.add_toast(Adw.Toast(title=_("Copied"), timeout=_TOAST_SECONDS))

    def _on_clear(self, _button: Gtk.Button) -> None:
        """S2: clearing can be undone for a few seconds."""
        before = self._service.clear()
        if len(before) == len(self._service.items):
            return  # only pinned entries, or nothing: there is nothing to undo
        toast = Adw.Toast(title=_("History cleared"), button_label=_("Undo"), timeout=_UNDO_SECONDS)
        toast.connect("button-clicked", lambda _toast: self._service.restore(before))
        self._toasts.add_toast(toast)

    def _build_row(self, entry: ClipEntry) -> Adw.ActionRow:
        row = Adw.ActionRow(
            title=entry.label, subtitle=_(_KIND_LABELS[entry.kind]), activatable=True
        )
        row.add_prefix(Gtk.Image(icon_name=_KIND_ICONS[entry.kind]))
        row.connect("activated", lambda _r, text=entry.text: self._copy(text))

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
