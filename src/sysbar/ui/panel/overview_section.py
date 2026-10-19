"""Top of the panel: one line on the state of the machine, then the quick toggles.

P4 puts the answer to "is anything wrong?" above the numbers; P5 brings the
quick toggles, otherwise reachable only from the right-click menu, to the
window a left click opens. What to say and which tiles exist is decided in
:mod:`sysbar.app.panel_summary`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ...app.panel_summary import PanelSummary, QuickTile  # noqa: E402

TileCallback = Callable[[str], None]

_OK_ICON = "emblem-ok-symbolic"
_WARNING_ICON = "dialog-warning-symbolic"
_TILE_COLUMNS = 2


class OverviewSection(Gtk.Box):
    """Summary row plus a grid of toggle buttons."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._on_tile: TileCallback | None = None
        self._summary = Adw.ActionRow(visible=False)
        self._summary_icon = Gtk.Image(icon_name=_OK_ICON)
        self._summary.add_prefix(self._summary_icon)
        summary_list = Gtk.ListBox(
            css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE
        )
        summary_list.append(self._summary)
        self.append(summary_list)
        self._tiles = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE,
            min_children_per_line=_TILE_COLUMNS,
            max_children_per_line=_TILE_COLUMNS,
            homogeneous=True,
            column_spacing=8,
            row_spacing=8,
        )
        self.append(self._tiles)
        self._buttons: dict[str, Gtk.ToggleButton] = {}

    def bind_tiles(self, on_tile: TileCallback) -> None:
        self._on_tile = on_tile

    def set_summary(self, summary: PanelSummary) -> None:
        self._summary.set_visible(True)
        self._summary.set_title(summary.title)
        self._summary.set_subtitle(summary.detail)
        self._summary_icon.set_from_icon_name(_OK_ICON if summary.ok else _WARNING_ICON)
        for css, wanted in (("success", summary.ok), ("warning", not summary.ok)):
            if wanted:
                self._summary_icon.add_css_class(css)
            else:
                self._summary_icon.remove_css_class(css)

    def set_tiles(self, tiles: Sequence[QuickTile]) -> None:
        """Rebuild only when the set of tiles changes; otherwise update in place."""
        if [tile.id for tile in tiles] != list(self._buttons):
            self._tiles.remove_all()
            self._buttons = {tile.id: self._build_tile(tile.id) for tile in tiles}
            for button in self._buttons.values():
                self._tiles.append(button)
        for tile in tiles:
            self._apply(self._buttons[tile.id], tile)

    def _build_tile(self, tile_id: str) -> Gtk.ToggleButton:
        button = Gtk.ToggleButton(child=Adw.ButtonContent(can_shrink=True))
        # "clicked" fires only on user activation; set_active() in _apply emits
        # "toggled" alone, so a refresh never flips the system setting.
        button.connect("clicked", self._on_clicked, tile_id)
        return button

    def _on_clicked(self, _button: Gtk.ToggleButton, tile_id: str) -> None:
        if self._on_tile is not None:
            self._on_tile(tile_id)

    @staticmethod
    def _apply(button: Gtk.ToggleButton, tile: QuickTile) -> None:
        content = button.get_child()
        content.set_label(tile.label)
        content.set_icon_name(tile.icon_name)
        button.set_active(tile.active)
        # The checked style alone is too faint to read "on" at a glance.
        if tile.active:
            button.add_css_class("suggested-action")
        else:
            button.remove_css_class("suggested-action")
