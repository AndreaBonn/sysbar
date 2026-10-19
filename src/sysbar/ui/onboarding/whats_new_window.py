"""Shown once after an update: what is new in Sysbar and where to find it (O7)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ...app.whats_new import Note  # noqa: E402
from ...core.i18n import _  # noqa: E402

_WINDOW_WIDTH = 460
_WINDOW_HEIGHT = 600


class WhatsNewWindow(Adw.Window):
    """A short list of new features; closing it in any way marks them as seen."""

    def __init__(self, notes: Sequence[Note], on_seen: Callable[[], None]) -> None:
        super().__init__(title=_("What's new in Sysbar"))
        self.set_default_size(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self._on_seen = on_seen
        group = Adw.PreferencesGroup(
            title=_("What's new"), description=_("A quick look at what changed in this update.")
        )
        for note in notes:
            row = Adw.ActionRow(title=_(note.title), subtitle=_(note.detail))
            row.add_prefix(Gtk.Image(icon_name=note.icon_name))
            group.add(row)
        page = Adw.PreferencesPage()
        page.add(group)
        done = Gtk.Button(label=_("Got it"), css_classes=["suggested-action", "pill"])
        done.connect("clicked", lambda _button: self.close())
        bottom = Gtk.Box(halign=Gtk.Align.CENTER, margin_top=12, margin_bottom=16)
        bottom.append(done)
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        toolbar.set_content(page)
        toolbar.add_bottom_bar(bottom)
        self.set_content(toolbar)
        self.connect("close-request", self._on_close_request)

    def _on_close_request(self, _window: Adw.Window) -> bool:
        self._on_seen()
        return False
