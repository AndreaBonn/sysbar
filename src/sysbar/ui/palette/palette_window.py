"""The command palette: one shortcut, one search box, everything behind it.

Boundary code. What is listed, in what order, what is masked and what cannot be
run is decided in :mod:`sysbar.services.palette` and
:mod:`sysbar.app.palette_entries`; this window draws rows and routes keys.

Three behaviours are the point of the window, not decoration:

* the search box holds the focus from the moment it opens, so the first
  keystroke after the shortcut is already part of the query;
* the arrow keys move through the results while the focus stays in the search
  box, which is what makes type-then-Enter one movement rather than three;
* losing focus closes it, so a palette summoned by accident does not sit on
  screen listing past clipboard entries.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from ...core.i18n import _  # noqa: E402
from ...services.palette.matcher import next_index  # noqa: E402
from ...services.palette.models import PaletteEntry  # noqa: E402

SearchCallback = Callable[[str], Sequence[PaletteEntry]]

_WINDOW_WIDTH = 640
_WINDOW_HEIGHT = 460
_REVEAL_ICON = "view-reveal-symbolic"
_MOVE_DOWN = 1
_MOVE_UP = -1


class PaletteWindow(Adw.Window):
    """A search box over every action, scene, clip, shelf item and device."""

    def __init__(self, search: SearchCallback) -> None:
        # Not modal: Sysbar has no main window to be transient for, and a modal
        # grab without a transient parent has nothing to hold in a window group,
        # so it would claim a restriction it does not enforce.
        super().__init__(title=_("Command palette"))
        self.set_default_size(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self._search = search
        self._closing = False
        self._entry = Gtk.SearchEntry(placeholder_text=_("Search actions, scenes, clips…"))
        self._list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.BROWSE)
        self._empty = Adw.StatusPage(
            title=_("No matches"),
            description=_("Try a shorter query."),
            icon_name="system-search-symbolic",
        )
        self._stack = Gtk.Stack()
        self._rows: list[PaletteEntry] = []
        self._build_content()
        self._install_key_handling()
        self._entry.connect("search-changed", lambda _entry: self._refresh())
        self._list.connect("row-activated", self._on_row_activated)
        self.connect("notify::is-active", self._on_active_changed)
        self._refresh()

    # --- construction -----------------------------------------------------

    def _build_content(self) -> None:
        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(self._list)
        self._stack.add_named(scroller, "results")
        self._stack.add_named(self._empty, "empty")

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for margin in ("top", "bottom", "start", "end"):
            getattr(content, f"set_margin_{margin}")(12)
        content.append(self._entry)
        content.append(self._stack)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar(show_end_title_buttons=False))
        toolbar.set_content(content)
        self.set_content(toolbar)

    def _install_key_handling(self) -> None:
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key_pressed)
        # Attached to the window rather than the entry so the keys work wherever
        # the focus happens to be, including on a row reached by Tab.
        self.add_controller(controller)

    def do_map(self) -> None:
        """Put the caret in the search box before the first frame is drawn."""
        Adw.Window.do_map(self)
        self._entry.grab_focus()

    # --- keyboard ---------------------------------------------------------

    def _on_key_pressed(
        self, _controller: Gtk.EventControllerKey, keyval: int, _keycode: int, _state: int
    ) -> bool:
        if keyval == Gdk.KEY_Escape:
            self._dismiss()
            return True
        if keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
            self._move_selection(_MOVE_DOWN if keyval == Gdk.KEY_Down else _MOVE_UP)
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self._activate_selected()
            return True
        return False

    def _move_selection(self, step: int) -> None:
        """Move through the results while the caret stays in the search box."""
        selected = self._list.get_selected_row()
        current = selected.get_index() if selected is not None else -1
        target = next_index(current, len(self._rows), step)
        row = self._list.get_row_at_index(target) if target >= 0 else None
        if row is None:
            return
        self._list.select_row(row)
        # Focusing the row is what makes the scrolled window bring it into view;
        # the caret then goes straight back to the entry so typing continues to
        # refine the query. Neither call touches window activation, which is a
        # window-manager notion, so this cannot trip the close-on-inactive path.
        row.grab_focus()
        self._entry.grab_focus_without_selecting()

    def _activate_selected(self) -> None:
        selected = self._list.get_selected_row()
        if selected is None:
            return
        self._run(selected.get_index())

    def _on_row_activated(self, _list: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        self._run(row.get_index())

    def _run(self, index: int) -> None:
        """Invoke the entry at ``index`` and close, unless it cannot be run."""
        if not 0 <= index < len(self._rows):
            return
        if self._rows[index].activate():
            self._dismiss()

    def _on_active_changed(self, *_args: object) -> None:
        if not self.get_property("is-active"):
            self._dismiss()

    def _dismiss(self) -> None:
        """Close once, however many times the request arrives.

        Closing drops the window's activation, which fires ``notify::is-active``
        again and re-enters here. The guard makes that idempotence explicit
        rather than leaving it to how GTK happens to order the two.
        """
        if self._closing:
            return
        self._closing = True
        # ``close`` emits ``close-request``, which is what clears the window slot
        # that owns this instance, so there is nothing else to notify.
        self.close()

    # --- results ----------------------------------------------------------

    def _refresh(self) -> None:
        entries = list(self._search(self._entry.get_text()))
        self._rows = entries
        self._list.remove_all()
        for entry in entries:
            self._list.append(_build_row(entry))
        self._stack.set_visible_child_name("results" if entries else "empty")
        first = self._list.get_row_at_index(0)
        if first is not None:
            self._list.select_row(first)


def _build_row(entry: PaletteEntry) -> Adw.ActionRow:
    """One result row: title, context, and a reveal button when masked."""
    row = Adw.ActionRow(
        title=entry.title,
        subtitle=entry.unavailable_reason or entry.subtitle,
        activatable=entry.is_runnable,
        sensitive=entry.is_runnable,
    )
    if entry.masked:
        row.add_suffix(_reveal_button(row, entry))
    return row


def _reveal_button(row: Adw.ActionRow, entry: PaletteEntry) -> Gtk.Button:
    """Swap a masked title for its real content, on an explicit click.

    Masked entries are shown that way because the palette can be summoned over
    a shared screen; revealing is therefore a deliberate act, never the default.
    """
    button = Gtk.Button(
        icon_name=_REVEAL_ICON,
        tooltip_text=_("Reveal"),
        valign=Gtk.Align.CENTER,
    )
    button.add_css_class("flat")
    button.connect("clicked", lambda _button: row.set_title(entry.haystack))
    return button
