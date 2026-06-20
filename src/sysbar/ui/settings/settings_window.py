"""Preferences window: one page per feature, bound live to GSettings."""

from __future__ import annotations

from collections.abc import Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

from ... import __version__  # noqa: E402
from ...core.config import Config  # noqa: E402
from ...core.i18n import _  # noqa: E402
from ...core.localization import install_language  # noqa: E402
from ...services.autostart import AutostartManager  # noqa: E402
from ..footer import build_footer  # noqa: E402
from .widgets import ComboBinding, bound_spin, bound_switch  # noqa: E402

_LANGUAGE_KEY = "app-language"

_LANGUAGES = [("", "System"), ("en", "English"), ("it", "Italiano")]
_INTERVALS = [(1, "1 second"), (2, "2 seconds"), (5, "5 seconds")]
_TEMPERATURE_UNITS = [("celsius", "Celsius"), ("fahrenheit", "Fahrenheit")]
_MEMORY_STYLES = [("dot", "Dot"), ("percent", "Percent"), ("both", "Both")]
_PLACEMENTS = [("off", "Off"), ("bar", "Bar"), ("menu", "Menu")]
_TRAY_METRIC_ROWS = [
    ("cpu", "menu-bar-cpu-placement", "CPU"),
    ("gpu", "menu-bar-gpu-placement", "GPU"),
    ("memory", "menu-bar-memory-placement", "Memory"),
    ("network", "menu-bar-network-placement", "Network"),
    ("battery", "menu-bar-battery-placement", "Battery"),
    ("power", "menu-bar-power-placement", "Power"),
]
_GRAPH_ROWS = [
    ("monitor-graph-cpu", "CPU"),
    ("monitor-graph-gpu", "GPU"),
    ("monitor-graph-memory", "Memory"),
    ("monitor-graph-network", "Network"),
    ("monitor-graph-power", "Power"),
    ("monitor-graph-battery", "Battery"),
]
_DURATIONS = [(0, "Indefinite"), (15, "15 min"), (30, "30 min"), (60, "1 hour"), (120, "2 hours")]
_BATTERY_LIMITS = [(0, "Never"), (5, "5%"), (10, "10%"), (15, "15%"), (20, "20%")]


class SettingsWindow(Adw.PreferencesWindow):
    """Live-bound preferences, one page per feature."""

    def __init__(
        self,
        config: Config,
        autostart: AutostartManager,
        unavailable_metrics: frozenset[str] = frozenset(),
    ) -> None:
        super().__init__(title=_("Sysbar Preferences"))
        self.set_default_size(640, 560)
        self._config = config
        self._settings = config.settings
        self._autostart = autostart
        self._unavailable_metrics = unavailable_metrics
        self._combos: list[ComboBinding] = []

        self.add(self._general_page())
        self.add(self._monitor_page())
        self.add(self._alerts_page())
        self.add(self._keep_awake_page())
        self.add(self._features_page())
        self.add(self._about_page())

        self._language_handler = self._settings.connect(
            f"changed::{_LANGUAGE_KEY}", self._on_language_changed
        )
        self.connect("close-request", self._on_close_request)

    def _combo(
        self, key: str, title: str, options: Sequence[tuple[object, str]], is_int: bool
    ) -> Adw.ComboRow:
        binding = ComboBinding(self._settings, key, title, options, is_int)
        self._combos.append(binding)
        return binding.row

    def _general_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title=_("General"), icon_name="preferences-system-symbolic")
        group = Adw.PreferencesGroup(title=_("General"))
        group.add(self._combo(_LANGUAGE_KEY, "Language", _LANGUAGES, is_int=False))

        autostart_row = Adw.SwitchRow(title=_("Start at login"))
        autostart_row.set_active(self._autostart.is_enabled())
        autostart_row.connect("notify::active", self._on_autostart_toggled)
        group.add(autostart_row)

        group.add(bound_switch(self._settings, "auto-check-updates", "Check for updates"))
        page.add(group)
        return page

    def _monitor_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(
            title=_("Monitor"), icon_name="utilities-system-monitor-symbolic"
        )

        tray = Adw.PreferencesGroup(
            title=_("Tray metrics"),
            description=_("Off, in the always-visible bar, or in the dropdown menu"),
        )
        for metric, key, title in _TRAY_METRIC_ROWS:
            row = self._combo(key, title, _PLACEMENTS, is_int=False)
            if metric in self._unavailable_metrics:
                row.set_sensitive(False)
                row.set_subtitle(_("Not detected on this system"))
            tray.add(row)
        page.add(tray)

        options = Adw.PreferencesGroup(title=_("Sampling"))
        options.add(self._combo("monitor-interval-seconds", "Interval", _INTERVALS, is_int=True))
        options.add(self._combo("temperature-unit", "Temperature", _TEMPERATURE_UNITS, False))
        options.add(self._combo("menu-bar-memory-style", "Memory style", _MEMORY_STYLES, False))
        page.add(options)

        graphs = Adw.PreferencesGroup(
            title=_("History graphs"),
            description=_("Show a sparkline of recent values next to each metric"),
        )
        for key, title in _GRAPH_ROWS:
            graphs.add(bound_switch(self._settings, key, title))
        page.add(graphs)
        return page

    def _alerts_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title=_("Alerts"), icon_name="dialog-warning-symbolic")
        group = Adw.PreferencesGroup(
            title=_("Threshold alerts"),
            description=_("Notify when a metric crosses a limit. 0 turns an alert off."),
        )
        group.add(bound_switch(self._settings, "alert-enabled", "Enable alerts"))
        group.add(bound_spin(self._settings, "alert-cpu-percent", "CPU load (%)", 0, 100))
        group.add(bound_spin(self._settings, "alert-cpu-seconds", "CPU sustained for (s)", 0, 3600))
        group.add(bound_spin(self._settings, "alert-memory-percent", "Memory used (%)", 0, 100))
        group.add(bound_spin(self._settings, "alert-disk-percent", "Disk used (%)", 0, 100))
        group.add(
            bound_spin(self._settings, "alert-temperature-celsius", "Temperature (°C)", 0, 150)
        )
        group.add(bound_spin(self._settings, "alert-battery-percent", "Battery low (%)", 0, 100))
        page.add(group)
        return page

    def _keep_awake_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title=_("Keep Awake"), icon_name="weather-clear-symbolic")
        group = Adw.PreferencesGroup(title=_("Keep Awake"))
        group.add(self._combo("default-duration-minutes", "Default duration", _DURATIONS, True))
        group.add(self._combo("battery-limit-percent", "Stop below battery", _BATTERY_LIMITS, True))
        group.add(bound_switch(self._settings, "hotkey-enabled", "Global hotkey"))
        group.add(bound_switch(self._settings, "show-countdown", "Show countdown in tray"))
        group.add(bound_switch(self._settings, "clamshell-preferred", "Keep awake with lid closed"))
        page.add(group)
        return page

    def _features_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title=_("Features"), icon_name="view-grid-symbolic")
        group = Adw.PreferencesGroup(
            title=_("Features"), description=_("Each feature is off by default")
        )
        group.add(bound_switch(self._settings, "monitor-show-mixer", "Volume mixer"))
        group.add(bound_switch(self._settings, "auto-quit-enabled", "Auto-quit closed apps"))
        group.add(bound_switch(self._settings, "shelf-enabled", "Shelf"))
        group.add(bound_switch(self._settings, "shelf-shake-to-open", "Shelf: shake to open"))
        group.add(bound_switch(self._settings, "clipboard-enabled", "Clipboard history"))
        page.add(group)
        return page

    def _about_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title=_("About"), icon_name="help-about-symbolic")
        group = Adw.PreferencesGroup(title=_("About"))
        group.add(Adw.ActionRow(title=_("Version"), subtitle=__version__))

        restart_row = Adw.ActionRow(title=_("Run onboarding again"))
        button = Gtk.Button(label=_("Restart"), valign=Gtk.Align.CENTER)
        button.connect("clicked", self._on_restart_onboarding)
        restart_row.add_suffix(button)
        restart_row.set_activatable_widget(button)
        group.add(restart_row)
        page.add(group)

        credit = Adw.PreferencesGroup()
        credit.add(build_footer())
        page.add(credit)
        return page

    def _on_autostart_toggled(self, row: Adw.SwitchRow, _param: object) -> None:
        self._autostart.set_enabled(row.get_active())

    def _on_language_changed(self, settings: Gio.Settings, _key: str) -> None:
        """Reinstall the catalog and prompt for a restart (already-built UI stays as-is)."""
        install_language(settings.get_string(_LANGUAGE_KEY))
        self.add_toast(Adw.Toast(title=_("Restart Sysbar to apply the language")))

    def _on_close_request(self, _window: Adw.PreferencesWindow) -> bool:
        self._settings.disconnect(self._language_handler)
        return False

    def _on_restart_onboarding(self, _button: Gtk.Button) -> None:
        self._settings.set_boolean("has-onboarded", False)
        self._settings.set_int("onboarding-step", 0)
