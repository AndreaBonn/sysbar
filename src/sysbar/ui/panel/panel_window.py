"""Tray panel window.

A borderless window kept above other windows, shown next to the tray icon. In
this milestone it lays out the monitor sections as placeholders; the live
metrics are filled in by the system monitor milestone.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ...core.constants import PANEL_SECTION_ORDER  # noqa: E402

_SECTION_TITLES = {
    "system": "System",
    "network": "Network",
    "power": "Power",
    "mixer": "Mixer",
    "fan_control": "Fan Control (beta)",
}
_PANEL_WIDTH = 360
_PANEL_HEIGHT = 480


class PanelWindow(Adw.Window):
    """The popover-style panel anchored to the tray."""

    def __init__(self) -> None:
        super().__init__(title="Sysbar", decorated=False, resizable=False)
        self.set_default_size(_PANEL_WIDTH, _PANEL_HEIGHT)
        self.add_css_class("sysbar-panel")
        self._build_content()

    def _build_content(self) -> None:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar(show_start_title_buttons=False, show_end_title_buttons=True)
        header.set_title_widget(Gtk.Label(label="Sysbar"))
        toolbar.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        for section in PANEL_SECTION_ORDER:
            content.append(self._section_placeholder(section))

        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(content)
        toolbar.set_content(scroller)
        self.set_content(toolbar)

    def _section_placeholder(self, section: str) -> Gtk.Widget:
        group = Adw.PreferencesGroup(title=_SECTION_TITLES.get(section, section))
        group.add(Adw.ActionRow(title="No data yet", subtitle="Populated by the system monitor"))
        return group
