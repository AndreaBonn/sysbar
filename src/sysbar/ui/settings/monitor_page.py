"""Preferences > Monitor: where each value appears, with the top bar previewed live.

I3: the placement names are places ("Top bar", "Menu only", "Hidden") rather
than internal states, and a preview row shows what the bar will read after each
change, so the effect is visible without looking up at the panel.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib  # noqa: E402

from ...app.settings_content import PLACEMENT_OPTIONS, tray_preview_text  # noqa: E402
from ...core.i18n import _  # noqa: E402
from .widgets import ComboBinding, bound_switch  # noqa: E402

_INTERVALS = [(1, "1 second"), (2, "2 seconds"), (5, "5 seconds")]
_TEMPERATURE_UNITS = [("celsius", "Celsius"), ("fahrenheit", "Fahrenheit")]
_MEMORY_STYLES = [("dot", "Dot"), ("percent", "Percent"), ("both", "Both")]
_TRAY_METRIC_ROWS = [
    ("cpu", "CPU"),
    ("gpu", "GPU"),
    ("memory", "Memory"),
    ("network", "Network"),
    ("battery", "Battery"),
    ("power", "Power"),
]
_GRAPH_ROWS = [
    ("monitor-graph-cpu", "CPU"),
    ("monitor-graph-gpu", "GPU"),
    ("monitor-graph-memory", "Memory"),
    ("monitor-graph-network", "Network"),
    ("monitor-graph-power", "Power"),
    ("monitor-graph-battery", "Battery"),
]
_PREVIEW_REFRESH_SECONDS = 2
# Settings whose change alters what the top bar reads.
_PREVIEW_KEY_PREFIXES = ("menu-bar-", "temperature-unit")


class MonitorPage(Adw.PreferencesPage):
    """Placement of each metric, sampling options and history graphs."""

    def __init__(
        self,
        settings: Gio.Settings,
        unavailable_metrics: frozenset[str],
        tray_preview: Callable[[], str | None],
    ) -> None:
        super().__init__(title=_("Monitor"), icon_name="utilities-system-monitor-symbolic")
        self._settings = settings
        self._tray_preview = tray_preview
        self._combos: list[ComboBinding] = []
        self._preview = Adw.ActionRow(title=_("Top bar preview"))
        self._preview.add_css_class("property")
        self.add(self._placement_group(unavailable_metrics))
        self.add(self._sampling_group())
        self.add(self._graphs_group())
        self._refresh_preview()
        self._handler = settings.connect("changed", self._on_changed)
        # New samples change the reading too, not only settings changes.
        self._timer = GLib.timeout_add_seconds(_PREVIEW_REFRESH_SECONDS, self._on_tick)

    def disconnect_settings(self) -> None:
        self._settings.disconnect(self._handler)
        GLib.source_remove(self._timer)

    def _on_tick(self) -> bool:
        self._refresh_preview()
        return True

    def _combo(
        self, key: str, title: str, options: Sequence[tuple[object, str]], is_int: bool
    ) -> Adw.ComboRow:
        binding = ComboBinding(self._settings, key, title, options, is_int)
        self._combos.append(binding)
        return binding.row

    def _placement_group(self, unavailable: frozenset[str]) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title=_("Tray metrics"),
            description=_(
                "Choose where each value appears: always visible in the top bar, "
                "only in the menu, or hidden."
            ),
        )
        group.add(self._preview)
        for metric, title in _TRAY_METRIC_ROWS:
            row = self._combo(
                f"menu-bar-{metric}-placement", title, PLACEMENT_OPTIONS, is_int=False
            )
            if metric in unavailable:
                row.set_sensitive(False)
                row.set_subtitle(_("Not detected on this system"))
            group.add(row)
        group.add(
            bound_switch(
                self._settings,
                "menu-show-device-batteries",
                "Device batteries",
                "List connected keyboards, mice and headsets in the menu",
            )
        )
        return group

    def _sampling_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=_("Sampling"))
        group.add(self._combo("monitor-interval-seconds", "Interval", _INTERVALS, is_int=True))
        group.add(self._combo("temperature-unit", "Temperature", _TEMPERATURE_UNITS, False))
        group.add(self._combo("menu-bar-memory-style", "Memory style", _MEMORY_STYLES, False))
        return group

    def _graphs_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title=_("History graphs"),
            description=_("Show a sparkline of recent values next to each metric"),
        )
        for key, title in _GRAPH_ROWS:
            group.add(bound_switch(self._settings, key, title))
        return group

    def _on_changed(self, _settings: Gio.Settings, key: str) -> None:
        if key.startswith(_PREVIEW_KEY_PREFIXES):
            self._refresh_preview()

    def _refresh_preview(self) -> None:
        self._preview.set_subtitle(tray_preview_text(self._tray_preview()))
