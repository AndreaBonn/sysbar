"""Application life cycle.

A single-instance ``Adw.Application`` with no main window: Sysbar lives in the
tray. The tray (StatusNotifierItem + dbusmenu) is registered on the session bus
once the application is registered. Feature services are wired in later
milestones; here the shell, panel, settings and onboarding are in place.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib  # noqa: E402

from ..core.capabilities import (  # noqa: E402
    PIPEWIRE_PULSE,
    POLKIT,
    SESSION_X11,
    Capabilities,
)
from ..core.config import Config  # noqa: E402
from ..core.constants import (  # noqa: E402
    APP_ID,
    AUTO_QUIT_SYSTEM_WHITELIST,
    CAPABILITY_REFRESH_INTERVAL_SECONDS,
    CURRENT_FEATURE_SET,
    HARDWARE_OPTIONAL_METRICS,
    PLACEMENT_MENU,
    PLACEMENT_OFF,
    SHELF_DIR,
    TRAY_METRICS,
)
from ..core.i18n import _  # noqa: E402
from ..core.localization import install_language  # noqa: E402
from ..services.audio.app_volume_mixer import AppVolumeMixer  # noqa: E402
from ..services.audio.pulse_backend import PulseAudioBackend  # noqa: E402
from ..services.auto_quit.os_terminator import OsTerminator  # noqa: E402
from ..services.auto_quit.service import AutoQuitService  # noqa: E402
from ..services.autostart import AutostartManager  # noqa: E402
from ..services.keep_awake.inhibitor import SystemInhibitor  # noqa: E402
from ..services.keep_awake.manager import KeepAwakeManager  # noqa: E402
from ..services.keep_awake.ports import EndReason  # noqa: E402
from ..services.keep_awake.scheduler import GLibScheduler  # noqa: E402
from ..services.metrics import metric_format as mf  # noqa: E402
from ..services.notifier import Notifier  # noqa: E402
from ..services.shelf.shake_monitor import ShakeMonitor  # noqa: E402
from ..services.shelf.shelf_service import ShelfService  # noqa: E402
from ..services.system_monitor.adapters import SysfsPowerReader  # noqa: E402
from ..services.system_monitor.alerting import AlertEngine, AlertThresholds  # noqa: E402
from ..services.system_monitor.monitor import SystemMonitor  # noqa: E402
from ..services.system_monitor.snapshot import SystemSnapshot  # noqa: E402
from ..services.uninstall.app_uninstaller import AppUninstaller  # noqa: E402
from ..services.uninstall.command_query import CommandPackageQuery  # noqa: E402
from ..services.uninstall.package_remover import PkexecPackageRemover  # noqa: E402
from ..services.uninstall.trash import GioTrash  # noqa: E402
from ..services.update_service import UpdateInfo, UpdateService  # noqa: E402
from .tray.menu_builder import MenuActions, build_menu_items  # noqa: E402
from .tray.menu_model import MenuModel  # noqa: E402
from .tray.tray import Tray  # noqa: E402
from .tray_renderer import (  # noqa: E402
    TrayOptions,
    available_metrics,
    menu_metric_values,
    render_tray_label,
)

_KEEP_AWAKE_PLAY = "▶"
_SESSION_END_MESSAGES = {
    EndReason.TIMER.value: "Keep awake ended (timer elapsed)",
    EndReason.BATTERY.value: "Keep awake ended (battery low)",
}

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
        self._alert_engine: AlertEngine | None = None
        self._keep_awake: KeepAwakeManager | None = None
        self._mixer: AppVolumeMixer | None = None
        self._shelf: ShelfService | None = None
        self._shelf_window: Adw.Window | None = None
        self._shake_monitor: ShakeMonitor | None = None
        self._auto_quit: AutoQuitService | None = None
        self._uninstaller: AppUninstaller | None = None
        self._uninstaller_window: Adw.Window | None = None
        self._notifier: Notifier | None = None
        self._countdown_timer = 0
        self._held = False

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        self._config = Config()
        self._config.migrate_legacy_placements()
        install_language(self._config.get_string("app-language"))
        self._capabilities.refresh()
        self._notifier = Notifier(self)
        self._install_actions()
        self._setup_tray()
        self._setup_monitor()
        self._setup_alerting()
        self._setup_keep_awake()
        self._setup_mixer()
        self._reconcile_shelf()
        self._setup_auto_quit()
        self._setup_uninstaller()
        self._setup_update_check()
        GLib.timeout_add_seconds(CAPABILITY_REFRESH_INTERVAL_SECONDS, self._refresh_capabilities)
        log.info("application started", extra={"capabilities": self._capabilities.snapshot()})

    def _setup_monitor(self) -> None:
        self._monitor = SystemMonitor(self.config)
        self._monitor.connect("snapshot-updated", self._on_snapshot)
        self.config.settings.connect("changed", self._on_settings_changed)
        self._update_tray_active()

    def _setup_alerting(self) -> None:
        self._alert_engine = AlertEngine(thresholds=self._alert_thresholds)
        self._reconcile_alerting()

    def _alert_thresholds(self) -> AlertThresholds:
        config = self.config
        return AlertThresholds(
            cpu_percent=config.alert_cpu_percent,
            cpu_seconds=config.alert_cpu_seconds,
            memory_percent=config.alert_memory_percent,
            disk_percent=config.alert_disk_percent,
            temperature_celsius=config.alert_temperature_celsius,
            battery_percent=config.alert_battery_percent,
        )

    def _reconcile_alerting(self) -> None:
        if self._monitor is not None:
            self._monitor.set_alerting_active(self.config.alert_enabled)

    def _evaluate_alerts(self, snapshot: SystemSnapshot) -> None:
        if self._alert_engine is None or self._notifier is None or not self.config.alert_enabled:
            return
        for alert in self._alert_engine.evaluate(snapshot):
            self._notifier.notify(alert.title, alert.body, notification_id=f"alert-{alert.key}")

    def _setup_keep_awake(self) -> None:
        self._keep_awake = KeepAwakeManager(SystemInhibitor(), SysfsPowerReader(), GLibScheduler())
        self._keep_awake.connect("changed", self._on_keep_awake_changed)
        self._keep_awake.connect("session-ended", self._on_session_ended)

    def _setup_mixer(self) -> None:
        if not self._capabilities.has(PIPEWIRE_PULSE):
            return
        try:
            backend = PulseAudioBackend()
        except Exception as error:
            log.warning("audio backend unavailable", extra={"error": str(error)})
            return
        self._mixer = AppVolumeMixer(backend, self.config)
        self._mixer.start()

    def _setup_auto_quit(self) -> None:
        if not self._capabilities.has(SESSION_X11):
            return
        try:
            from ..services.auto_quit.wnck_source import WnckWindowSource

            source = WnckWindowSource()
        except Exception as error:
            log.warning("auto-quit unavailable", extra={"error": str(error)})
            return
        self._auto_quit = AutoQuitService(
            source=source,
            terminator=OsTerminator(),
            scheduler=GLibScheduler(),
            exceptions=lambda: self.config.auto_quit_exceptions,
            system_ids=AUTO_QUIT_SYSTEM_WHITELIST,
            enabled=lambda: self.config.get_bool("auto-quit-enabled"),
        )
        self._auto_quit.start()

    def _setup_update_check(self) -> None:
        if not self.config.get_bool("auto-check-updates"):
            return
        thread = threading.Thread(target=self._run_update_check, daemon=True)
        thread.start()

    def _run_update_check(self) -> None:
        info = UpdateService().check()
        if info is not None:
            GLib.idle_add(self._on_update_found, info)

    def _on_update_found(self, info: UpdateInfo) -> bool:
        if self._notifier is not None:
            self._notifier.notify(
                _("Sysbar update available"),
                f"{info.version} is available. Run: sudo apt update && sudo apt upgrade sysbar",
                notification_id="update",
            )
        return False

    def _setup_uninstaller(self) -> None:
        self._uninstaller = AppUninstaller(
            home=Path.home(),
            trash=GioTrash(),
            remover=PkexecPackageRemover(),
            polkit_available=self._capabilities.has(POLKIT),
        )

    def _open_uninstaller(self) -> None:
        if self._uninstaller is None:
            self._setup_uninstaller()
        from ..ui.uninstall.uninstaller_window import UninstallerWindow

        if self._uninstaller_window is None and self._uninstaller is not None:
            self._uninstaller_window = UninstallerWindow(self._uninstaller, CommandPackageQuery())
            self._uninstaller_window.connect("close-request", self._on_uninstaller_closed)
        if self._uninstaller_window is not None:
            self._uninstaller_window.present()

    def _on_uninstaller_closed(self, _window: Adw.Window) -> bool:
        self._uninstaller_window = None
        return False

    def _reconcile_shelf(self) -> None:
        enabled = self.config.get_bool("shelf-enabled")
        if enabled and self._shelf is None:
            self._shelf = ShelfService(SHELF_DIR)
            self._shelf.load()
        wants_shake = (
            enabled
            and self.config.get_bool("shelf-shake-to-open")
            and self._capabilities.has(SESSION_X11)
        )
        if wants_shake and self._shake_monitor is None:
            monitor = ShakeMonitor(on_shake=self._open_shelf)
            if monitor.start():
                self._shake_monitor = monitor
        elif not wants_shake and self._shake_monitor is not None:
            self._shake_monitor.stop()
            self._shake_monitor = None
        if self._tray is not None:
            self._tray.set_menu(self._build_menu())

    def _open_shelf(self) -> None:
        if self._shelf is None:
            self._shelf = ShelfService(SHELF_DIR)
            self._shelf.load()
        from ..ui.shelf.shelf_window import ShelfWindow

        if self._shelf_window is None:
            self._shelf_window = ShelfWindow(self._shelf)
            self._shelf_window.connect("close-request", self._on_shelf_closed)
        self._shelf_window.present()

    def _on_shelf_closed(self, _window: Adw.Window) -> bool:
        self._shelf_window = None
        return False

    def _update_tray_active(self) -> None:
        if self._monitor is None:
            return
        active = any(self.config.metric_placement(m) != PLACEMENT_OFF for m in TRAY_METRICS)
        self._monitor.set_tray_active(active)
        self._refresh_tray_label()
        self._refresh_menu()

    def _tray_options(self) -> TrayOptions:
        config = self.config
        placements = {metric: config.metric_placement(metric) for metric in TRAY_METRICS}
        return TrayOptions(
            memory_style=config.memory_style,
            temperature_unit=config.temperature_unit,
            **placements,
        )

    def _has_menu_metrics(self) -> bool:
        return any(self.config.metric_placement(m) == PLACEMENT_MENU for m in TRAY_METRICS)

    def _on_snapshot(self, _monitor: SystemMonitor, snapshot: SystemSnapshot) -> None:
        self._refresh_tray_label()
        self._evaluate_alerts(snapshot)
        if self._panel is not None:
            self._panel.update_snapshot(snapshot)

    def _refresh_menu(self) -> None:
        if self._tray is not None:
            self._tray.set_menu(self._build_menu())

    def _on_menu_about_to_show(self) -> bool:
        """Rebuild the menu with fresh metric values just before it opens.

        Returning ``True`` only when metrics live in the dropdown lets the host
        re-read the layout on demand instead of us churning it on every sample.
        """
        if not self._has_menu_metrics():
            return False
        self._refresh_menu()
        return True

    def _refresh_tray_label(self) -> None:
        if self._tray is None:
            return
        segments: list[str] = []
        countdown = self._countdown_text()
        if countdown:
            segments.append(countdown)
        if self._monitor is not None and self._monitor.latest is not None:
            metrics = render_tray_label(self._monitor.latest, self._tray_options())
            if metrics:
                segments.append(metrics)
        self._tray.set_label(" · ".join(segments))

    def _countdown_text(self) -> str:
        if self._keep_awake is None or not self._keep_awake.is_active:
            return ""
        if not self.config.get_bool("show-countdown"):
            return ""
        remaining = self._keep_awake.remaining_seconds()
        if remaining is None:
            return _KEEP_AWAKE_PLAY
        return f"{_KEEP_AWAKE_PLAY} {mf.format_countdown(remaining)}"

    def _on_settings_changed(self, _settings: Gio.Settings, key: str) -> None:
        self._update_tray_active()
        if key.startswith("shelf-"):
            self._reconcile_shelf()
        if key.startswith("alert-"):
            self._reconcile_alerting()

    def _on_keep_awake_changed(self, _manager: KeepAwakeManager) -> None:
        self._refresh_menu()
        self._reconcile_countdown()
        self._refresh_tray_label()

    def _on_session_ended(self, _manager: KeepAwakeManager, reason: str) -> None:
        message = _SESSION_END_MESSAGES.get(reason)
        if message and self._notifier is not None:
            self._notifier.notify("Sysbar", _(message), notification_id="keep-awake")

    def _toggle_keep_awake(self) -> None:
        if self._keep_awake is None:
            return
        config = self.config
        self._keep_awake.toggle(
            duration_minutes=config.default_duration_minutes,
            clamshell=config.get_bool("clamshell-preferred"),
            battery_limit=config.battery_limit_percent,
        )

    def _reconcile_countdown(self) -> None:
        wants = (
            self._keep_awake is not None
            and self._keep_awake.is_active
            and self.config.get_bool("show-countdown")
        )
        if wants and not self._countdown_timer:
            self._countdown_timer = GLib.timeout_add_seconds(1, self._on_countdown_tick)
        elif not wants and self._countdown_timer:
            GLib.source_remove(self._countdown_timer)
            self._countdown_timer = 0

    def _on_countdown_tick(self) -> bool:
        self._refresh_tray_label()
        if self._keep_awake is not None and self._keep_awake.is_active:
            return True
        self._countdown_timer = 0
        return False

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
            ("toggle-keep-awake", self._toggle_keep_awake),
            ("open-shelf", self._open_shelf),
            ("open-uninstaller", self._open_uninstaller),
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
        self._tray = Tray(
            on_activate=self._open_panel,
            on_menu_about_to_show=self._on_menu_about_to_show,
        )
        self._tray.register(connection)
        self._tray.set_menu(self._build_menu())

    def _menu_metric_values(self) -> dict[str, str]:
        if self._monitor is None or self._monitor.latest is None:
            return {}
        return menu_metric_values(self._monitor.latest, self._tray_options())

    def _menu_actions(self) -> MenuActions:
        return MenuActions(
            toggle_keep_awake=self._toggle_keep_awake,
            open_panel=self._open_panel,
            open_shelf=self._open_shelf,
            open_uninstaller=self._open_uninstaller,
            open_settings=self._open_settings,
            quit=self.quit,
        )

    def _build_menu(self) -> MenuModel:
        keep_awake_on = self._keep_awake is not None and self._keep_awake.is_active
        items = build_menu_items(
            self._menu_metric_values(),
            keep_awake_on=keep_awake_on,
            shelf_enabled=self.config.get_bool("shelf-enabled"),
            actions=self._menu_actions(),
        )
        return MenuModel(items)

    def _open_panel(self) -> None:
        from ..ui.panel.panel_window import PanelWindow

        if self._panel is None:
            self._panel = PanelWindow()
            self._panel.connect("close-request", self._on_panel_closed)
            if self._mixer is not None:
                self._panel.bind_mixer(self._mixer)
            else:
                self._panel.set_mixer_unavailable()
        self._panel.set_temperature_unit(self.config.temperature_unit)
        self._panel.set_show_fans(self.config.get_bool("monitor-show-fan-control-beta"))
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

        # Availability is frozen at open time. The window is recreated on every
        # open (close clears the reference), so a hardware change is picked up on
        # the next open rather than live in an already-open window.
        if self._settings_window is None:
            self._settings_window = SettingsWindow(
                self.config, self._autostart, self._unavailable_metrics()
            )
            self._settings_window.connect("close-request", self._on_settings_closed)
        self._settings_window.present()

    def _unavailable_metrics(self) -> frozenset[str]:
        """Hardware-optional metrics with no data in the latest snapshot.

        Fail-open: with no snapshot yet, nothing is reported unavailable so the
        Settings rows stay enabled rather than being disabled by mistake.
        """
        snapshot = self._monitor.latest if self._monitor is not None else None
        if snapshot is None:
            return frozenset()
        present = available_metrics(snapshot, TrayOptions())
        return frozenset(m for m in HARDWARE_OPTIONAL_METRICS if m not in present)

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
