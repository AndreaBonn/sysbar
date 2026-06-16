"""Application life cycle.

A single-instance ``Adw.Application`` with no main window: Sysbar lives in the
tray. The tray (StatusNotifierItem + dbusmenu) is registered on the session bus
once the application is registered. Feature services are wired in later
milestones; here the shell, panel, settings and onboarding are in place.
"""

from __future__ import annotations

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib  # noqa: E402

from ..core.capabilities import Capabilities  # noqa: E402
from ..core.config import Config  # noqa: E402
from ..core.constants import (  # noqa: E402
    APP_ID,
    CAPABILITY_REFRESH_INTERVAL_SECONDS,
    CURRENT_FEATURE_SET,
)
from ..core.localization import install_language  # noqa: E402
from ..services.autostart import AutostartManager  # noqa: E402
from ..services.system_monitor.monitor import SystemMonitor  # noqa: E402
from ..services.system_monitor.snapshot import SystemSnapshot  # noqa: E402
from .tray.menu_model import TYPE_SEPARATOR, MenuItem, MenuModel  # noqa: E402
from .tray.tray import Tray  # noqa: E402
from .tray_renderer import TrayOptions, render_tray_label  # noqa: E402

_TRAY_METRIC_KEYS = (
    "menu-bar-cpu",
    "menu-bar-gpu",
    "menu-bar-memory",
    "menu-bar-network",
    "menu-bar-battery",
    "menu-bar-power",
)

log = logging.getLogger(__name__)


class SysbarApplication(Adw.Application):
    """Top-level application object."""

    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self._config: Config | None = None
        self._capabilities = Capabilities()
        self._autostart = AutostartManager()
        self._tray: Tray | None = None
        self._panel: Adw.Window | None = None
        self._settings_window: Adw.PreferencesWindow | None = None
        self._monitor: SystemMonitor | None = None
        self._held = False

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        self._config = Config()
        install_language(self._config.get_string("app-language"))
        self._capabilities.refresh()
        self._install_actions()
        self._setup_tray()
        self._setup_monitor()
        GLib.timeout_add_seconds(CAPABILITY_REFRESH_INTERVAL_SECONDS, self._refresh_capabilities)
        log.info("application started", extra={"capabilities": self._capabilities.snapshot()})

    def _setup_monitor(self) -> None:
        self._monitor = SystemMonitor(self.config)
        self._monitor.connect("snapshot-updated", self._on_snapshot)
        self.config.settings.connect("changed", self._on_settings_changed)
        self._update_tray_active()

    def _update_tray_active(self) -> None:
        if self._monitor is None:
            return
        active = any(self.config.get_bool(key) for key in _TRAY_METRIC_KEYS)
        self._monitor.set_tray_active(active)
        if not active and self._tray is not None:
            self._tray.set_label("")

    def _tray_options(self) -> TrayOptions:
        config = self.config
        return TrayOptions(
            show_cpu=config.get_bool("menu-bar-cpu"),
            show_gpu=config.get_bool("menu-bar-gpu"),
            show_memory=config.get_bool("menu-bar-memory"),
            show_network=config.get_bool("menu-bar-network"),
            show_battery=config.get_bool("menu-bar-battery"),
            show_power=config.get_bool("menu-bar-power"),
            memory_style=config.memory_style,
            temperature_unit=config.temperature_unit,
        )

    def _on_snapshot(self, _monitor: SystemMonitor, snapshot: SystemSnapshot) -> None:
        if self._tray is not None:
            self._tray.set_label(render_tray_label(snapshot, self._tray_options()))
        if self._panel is not None:
            self._panel.update_snapshot(snapshot)

    def _on_settings_changed(self, _settings: Gio.Settings, _key: str) -> None:
        self._update_tray_active()

    def do_activate(self) -> None:
        if not self._held:
            self._held = True
            self.hold()
            if not self.config.get_bool("has-onboarded"):
                self._show_onboarding()
        else:
            self._open_panel()

    def _install_actions(self) -> None:
        for name, handler in (
            ("open-panel", self._open_panel),
            ("open-settings", self._open_settings),
            ("quit", self.quit),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _a, _p, fn=handler: fn())
            self.add_action(action)

    def _setup_tray(self) -> None:
        connection = self.get_dbus_connection()
        if connection is None:
            log.warning("no session bus connection; tray unavailable")
            return
        self._tray = Tray(on_activate=self._open_panel)
        self._tray.register(connection)
        self._tray.set_menu(self._build_menu())

    def _build_menu(self) -> MenuModel:
        return MenuModel(
            [
                MenuItem(label="Open panel", action=self._open_panel),
                MenuItem(label="Settings", action=self._open_settings),
                MenuItem(item_type=TYPE_SEPARATOR),
                MenuItem(label="Quit", action=self.quit),
            ]
        )

    def _open_panel(self) -> None:
        from ..ui.panel.panel_window import PanelWindow

        if self._panel is None:
            self._panel = PanelWindow()
            self._panel.connect("close-request", self._on_panel_closed)
        self._panel.set_temperature_unit(self.config.temperature_unit)
        if self._monitor is not None:
            self._monitor.set_panel_open(True)
            if self._monitor.latest is not None:
                self._panel.update_snapshot(self._monitor.latest)
        self._panel.present()

    def _on_panel_closed(self, _window: Adw.Window) -> bool:
        self._panel = None
        if self._monitor is not None:
            self._monitor.set_panel_open(False)
        return False

    def _open_settings(self) -> None:
        from ..ui.settings.settings_window import SettingsWindow

        if self._settings_window is None:
            self._settings_window = SettingsWindow(self.config, self._autostart)
            self._settings_window.connect("close-request", self._on_settings_closed)
        self._settings_window.present()

    def _on_settings_closed(self, _window: Adw.PreferencesWindow) -> bool:
        self._settings_window = None
        return False

    def _show_onboarding(self) -> None:
        from ..ui.onboarding.onboarding_window import OnboardingWindow

        window = OnboardingWindow(self._capabilities, on_finish=self._finish_onboarding)
        window.present()

    def _finish_onboarding(self) -> None:
        self.config.set_bool("has-onboarded", True)
        self.config.settings.set_int("features-onboarding-version", CURRENT_FEATURE_SET)

    def _refresh_capabilities(self) -> bool:
        self._capabilities.refresh()
        return True

    @property
    def capabilities(self) -> Capabilities:
        return self._capabilities

    @property
    def config(self) -> Config:
        if self._config is None:
            self._config = Config()
        return self._config
