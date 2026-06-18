"""Preferences window: one page per feature, bound live to GSettings."""

from __future__ import annotations

from collections.abc import Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ... import __version__  # noqa: E402
from ...core.config import Config  # noqa: E402
from ...core.i18n import _  # noqa: E402
from ...services.autostart import AutostartManager  # noqa: E402
from .widgets import ComboBinding, bound_switch  # noqa: E402

_LANGUAGES = [("", "System"), ("en", "English"), ("it", "Italiano")]
_INTERVALS = [(1, "1 second"), (2, "2 seconds"), (5, "5 seconds")]
_TEMPERATURE_UNITS = [("celsius", "Celsius"), ("fahrenheit", "Fahrenheit")]
_MEMORY_STYLES = [("dot", "Dot"), ("percent", "Percent"), ("both", "Both")]
_PLACEMENTS = [("off", "Off"), ("bar", "Bar"), ("menu", "Menu")]
_TRAY_METRIC_ROWS = [
    ("menu-bar-cpu-placement", "CPU"),
    ("menu-bar-gpu-placement", "GPU"),
    ("menu-bar-memory-placement", "Memory"),
    ("menu-bar-network-placement", "Network"),
    ("menu-bar-battery-placement", "Battery"),
    ("menu-bar-power-placement", "Power"),
]
_DURATIONS = [(0, "Indefinite"), (15, "15 min"), (30, "30 min"), (60, "1 hour"), (120, "2 hours")]
_BATTERY_LIMITS = [(0, "Never"), (5, "5%"), (10, "10%"), (15, "15%"), (20, "20%")]


class SettingsWindow(Adw.PreferencesWindow):
    """Live-bound preferences, one page per feature."""

    def __init__(self, config: Config, autostart: AutostartManager) -> None:
        super().__init__(title=_("Sysbar Preferences"))
        self.set_default_size(640, 560)
        self._config = config
        self._settings = config.settings
        self._autostart = autostart
        self._combos: list[ComboBinding] = []

        self.add(self._general_page())
        self.add(self._monitor_page())
        self.add(self._keep_awake_page())
        self.add(self._features_page())
        self.add(self._about_page())

    def _combo(
        self, key: str, title: str, options: Sequence[tuple[object, str]], is_int: bool
    ) -> Adw.ComboRow:
        binding = ComboBinding(self._settings, key, title, options, is_int)
        self._combos.append(binding)
        return binding.row

    def _general_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title=_("General"), icon_name="preferences-system-symbolic")
        group = Adw.PreferencesGroup(title="General")
        group.add(self._combo("app-language", "Language", _LANGUAGES, is_int=False))

        autostart_row = Adw.SwitchRow(title="Start at login")
        autostart_row.set_active(self._autostart.is_enabled())
        autostart_row.connect("notify::active", self._on_autostart_toggled)
        group.add(autostart_row)

        group.add(bound_switch(self._settings, "auto-check-updates", "Check for updates"))
        page.add(group)
        return page

    def _monitor_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title="Monitor", icon_name="utilities-system-monitor-symbolic")

        tray = Adw.PreferencesGroup(
            title="Tray metrics",
            description="Off, in the always-visible bar, or in the dropdown menu",
        )
        for key, title in _TRAY_METRIC_ROWS:
            tray.add(self._combo(key, title, _PLACEMENTS, is_int=False))
        page.add(tray)

        options = Adw.PreferencesGroup(title="Sampling")
        options.add(self._combo("monitor-interval-seconds", "Interval", _INTERVALS, is_int=True))
        options.add(self._combo("temperature-unit", "Temperature", _TEMPERATURE_UNITS, False))
        options.add(self._combo("menu-bar-memory-style", "Memory style", _MEMORY_STYLES, False))
        page.add(options)
        return page

    def _keep_awake_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title="Keep Awake", icon_name="weather-clear-symbolic")
        group = Adw.PreferencesGroup(title="Keep Awake")
        group.add(self._combo("default-duration-minutes", "Default duration", _DURATIONS, True))
        group.add(self._combo("battery-limit-percent", "Stop below battery", _BATTERY_LIMITS, True))
        group.add(bound_switch(self._settings, "hotkey-enabled", "Global hotkey"))
        group.add(bound_switch(self._settings, "show-countdown", "Show countdown in tray"))
        group.add(bound_switch(self._settings, "clamshell-preferred", "Keep awake with lid closed"))
        page.add(group)
        return page

    def _features_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title=_("Features"), icon_name="view-grid-symbolic")
        group = Adw.PreferencesGroup(title="Features", description="Each feature is off by default")
        group.add(bound_switch(self._settings, "monitor-show-mixer", "Volume mixer"))
        group.add(bound_switch(self._settings, "auto-quit-enabled", "Auto-quit closed apps"))
        group.add(bound_switch(self._settings, "shelf-enabled", "Shelf"))
        group.add(bound_switch(self._settings, "shelf-shake-to-open", "Shelf: shake to open"))
        page.add(group)
        return page

    def _about_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title=_("About"), icon_name="help-about-symbolic")
        group = Adw.PreferencesGroup(title="About")
        group.add(Adw.ActionRow(title="Version", subtitle=__version__))

        restart_row = Adw.ActionRow(title="Run onboarding again")
        button = Gtk.Button(label="Restart", valign=Gtk.Align.CENTER)
        button.connect("clicked", self._on_restart_onboarding)
        restart_row.add_suffix(button)
        restart_row.set_activatable_widget(button)
        group.add(restart_row)
        page.add(group)
        return page

    def _on_autostart_toggled(self, row: Adw.SwitchRow, _param: object) -> None:
        self._autostart.set_enabled(row.get_active())

    def _on_restart_onboarding(self, _button: Gtk.Button) -> None:
        self._settings.set_boolean("has-onboarded", False)
        self._settings.set_int("onboarding-step", 0)
