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

from gi.repository import Adw, Gdk, Gio, GLib  # noqa: E402

from ..core.branding import register_app_icons  # noqa: E402
from ..core.capabilities import (  # noqa: E402
    GLOBAL_SHORTCUTS,
    GNOME_DESKTOP,
    PIPEWIRE_PULSE,
    POLKIT,
    PROC_NET_STATS,
    SESSION_X11,
    WAYLAND_WINDOW_SOURCE,
    Capabilities,
)
from ..core.config import Config  # noqa: E402
from ..core.constants import (  # noqa: E402
    APP_ID,
    AUTHOR_GITHUB_URL,
    AUTO_QUIT_SYSTEM_WHITELIST,
    CAPABILITY_REFRESH_INTERVAL_SECONDS,
    CLIPBOARD_DIR,
    CLIPBOARD_SHORTCUT_DESCRIPTION,
    CLIPBOARD_SHORTCUT_ID,
    CURRENT_FEATURE_SET,
    FOCUS_SCENE_SHORTCUT_DESCRIPTION,
    FOCUS_SCENE_SHORTCUT_ID,
    GNOME_INTERFACE_SCHEMA,
    GNOME_NOTIFICATIONS_SCHEMA,
    GRAPH_METRICS,
    HARDWARE_OPTIONAL_METRICS,
    KEEP_AWAKE_SHORTCUT_DESCRIPTION,
    KEEP_AWAKE_SHORTCUT_ID,
    NET_PROCESS_COUNT,
    PANEL_PROCESS_COUNT,
    PLACEMENT_MENU,
    PLACEMENT_OFF,
    SHELF_DIR,
    SHELF_SHORTCUT_DESCRIPTION,
    SHELF_SHORTCUT_ID,
    TRAY_METRICS,
)
from ..core.i18n import _  # noqa: E402
from ..core.localization import install_language  # noqa: E402
from ..services.audio.app_volume_mixer import AppVolumeMixer  # noqa: E402
from ..services.audio.device_switcher import DeviceSwitcher  # noqa: E402
from ..services.audio.pulse_backend import PulseAudioBackend  # noqa: E402
from ..services.auto_quit.os_terminator import OsTerminator  # noqa: E402
from ..services.auto_quit.ports import WindowSource  # noqa: E402
from ..services.auto_quit.service import AutoQuitService  # noqa: E402
from ..services.auto_quit.source_selection import (  # noqa: E402
    SOURCE_WAYLAND,
    SOURCE_X11,
    choose_window_source,
)
from ..services.autostart import AutostartManager  # noqa: E402
from ..services.clipboard.monitor import ClipboardMonitor  # noqa: E402
from ..services.clipboard.service import ClipboardService  # noqa: E402
from ..services.hotkey.manager import HotkeyBinding, HotkeyManager  # noqa: E402
from ..services.keep_awake.inhibitor import SystemInhibitor  # noqa: E402
from ..services.keep_awake.manager import KeepAwakeManager  # noqa: E402
from ..services.keep_awake.ports import EndReason  # noqa: E402
from ..services.keep_awake.scheduler import GLibScheduler  # noqa: E402
from ..services.metrics import metric_format as mf  # noqa: E402
from ..services.notifier import Notifier  # noqa: E402
from ..services.quick_toggles.adapters import (  # noqa: E402
    GioSettingsStore,
    PulseMicrophoneBackend,
)
from ..services.quick_toggles.desktop_toggles import (  # noqa: E402
    ColorSchemeToggle,
    DoNotDisturbToggle,
)
from ..services.quick_toggles.microphone import MicrophoneToggle  # noqa: E402
from ..services.scenes.adapters import CallbackSceneApplier, ConfigSceneWriter  # noqa: E402
from ..services.scenes.models import SCENE_FOCUS  # noqa: E402
from ..services.scenes.service import SceneService  # noqa: E402
from ..services.shelf.shake_monitor import ShakeMonitor  # noqa: E402
from ..services.shelf.shelf_service import ShelfService  # noqa: E402
from ..services.system_monitor.adapters import SysfsPowerReader  # noqa: E402
from ..services.system_monitor.alerting import AlertEngine, AlertThresholds  # noqa: E402
from ..services.system_monitor.history import MetricHistory  # noqa: E402
from ..services.system_monitor.monitor import SystemMonitor  # noqa: E402
from ..services.system_monitor.net_per_process import (  # noqa: E402
    NetRateTracker,
    SsNetSampler,
    top_by_throughput,
)
from ..services.system_monitor.processes import ProcessUsageService  # noqa: E402
from ..services.system_monitor.snapshot import SystemSnapshot  # noqa: E402
from ..services.system_monitor.termination import ProcessTerminationService  # noqa: E402
from ..services.uninstall.app_uninstaller import AppUninstaller  # noqa: E402
from ..services.uninstall.command_query import CommandPackageQuery  # noqa: E402
from ..services.uninstall.package_remover import PkexecPackageRemover  # noqa: E402
from ..services.uninstall.trash import GioTrash  # noqa: E402
from ..services.update_service import UpdateInfo, UpdateService  # noqa: E402
from .tray.menu_builder import (  # noqa: E402
    MenuActions,
    QuickToggleState,
    SceneMenuEntry,
    build_menu_items,
)
from .tray.menu_model import MenuModel  # noqa: E402
from .tray.tray import Tray  # noqa: E402
from .tray_renderer import (  # noqa: E402
    TrayOptions,
    available_metrics,
    menu_metric_values,
    render_device_rows,
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
        self._history = MetricHistory()
        self._alert_engine: AlertEngine | None = None
        self._process_usage = ProcessUsageService()
        self._net_tracker = NetRateTracker()
        self._net_sampler: SsNetSampler | None = None
        self._process_killer = ProcessTerminationService(OsTerminator(), GLibScheduler())
        self._keep_awake: KeepAwakeManager | None = None
        self._mixer: AppVolumeMixer | None = None
        self._device_switcher: DeviceSwitcher | None = None
        self._scenes: SceneService | None = None
        self._microphone: MicrophoneToggle | None = None
        self._dnd: DoNotDisturbToggle | None = None
        self._dark_mode: ColorSchemeToggle | None = None
        self._shelf: ShelfService | None = None
        self._shelf_window: Adw.Window | None = None
        self._shake_monitor: ShakeMonitor | None = None
        self._clipboard: ClipboardService | None = None
        self._clipboard_window: Adw.Window | None = None
        self._clipboard_monitor: ClipboardMonitor | None = None
        self._auto_quit: AutoQuitService | None = None
        self._hotkey: HotkeyManager | None = None
        self._uninstaller: AppUninstaller | None = None
        self._uninstaller_window: Adw.Window | None = None
        self._notifier: Notifier | None = None
        self._countdown_timer = 0
        self._held = False

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        register_app_icons(Gdk.Display.get_default())
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
        self._setup_hotkey()
        self._setup_mixer()
        self._setup_quick_toggles()
        self._setup_scenes()
        self._reconcile_shelf()
        self._reconcile_clipboard()
        self._setup_auto_quit()
        self._setup_uninstaller()
        self._setup_update_check()
        GLib.timeout_add_seconds(CAPABILITY_REFRESH_INTERVAL_SECONDS, self._refresh_capabilities)
        log.info("application started", extra={"capabilities": self._capabilities.snapshot()})

    def _setup_monitor(self) -> None:
        self._monitor = SystemMonitor(self.config)
        self._monitor.connect("snapshot-updated", self._on_snapshot)
        self.config.settings.connect("changed", self._on_settings_changed)
        if self._capabilities.has(PROC_NET_STATS):
            self._net_sampler = SsNetSampler()
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
        self._device_switcher = DeviceSwitcher(backend)

    def _setup_quick_toggles(self) -> None:
        if self._capabilities.has(PIPEWIRE_PULSE):
            try:
                self._microphone = MicrophoneToggle(PulseMicrophoneBackend())
            except Exception as error:
                log.warning("microphone backend unavailable", extra={"error": str(error)})
        if self._capabilities.has(GNOME_DESKTOP):
            self._dnd = DoNotDisturbToggle(GioSettingsStore(GNOME_NOTIFICATIONS_SCHEMA))
            self._dark_mode = ColorSchemeToggle(GioSettingsStore(GNOME_INTERFACE_SCHEMA))

    def _quick_toggle_state(self) -> QuickToggleState:
        return QuickToggleState(
            mic_available=self._microphone is not None,
            mic_muted=self._microphone.is_muted() if self._microphone is not None else False,
            mic_in_use=self._microphone.is_in_use() if self._microphone is not None else False,
            dnd_available=self._dnd is not None,
            dnd_active=self._dnd.is_active() if self._dnd is not None else False,
            dark_available=self._dark_mode is not None,
            dark_active=self._dark_mode.is_dark() if self._dark_mode is not None else False,
        )

    def _has_quick_toggles(self) -> bool:
        return any((self._microphone, self._dnd, self._dark_mode))

    def _setup_scenes(self) -> None:
        applier = CallbackSceneApplier(
            keep_awake=self._scene_set_keep_awake,
            do_not_disturb=self._scene_set_dnd,
            microphone_muted=self._scene_set_mic,
        )
        self._scenes = SceneService(
            ConfigSceneWriter(self.config),
            applier,
            active_id=self.config.get_string("active-scene"),
        )
        self._scenes.connect("changed", lambda _s: self._refresh_menu())

    def _scene_set_keep_awake(self, on: bool) -> None:
        if self._keep_awake is not None and self._keep_awake.is_active != on:
            self._toggle_keep_awake()

    def _scene_set_dnd(self, on: bool) -> None:
        if self._dnd is not None and self._dnd.is_active() != on:
            self._dnd.toggle()

    def _scene_set_mic(self, on: bool) -> None:
        if self._microphone is not None and self._microphone.is_muted() != on:
            self._microphone.toggle()

    def _activate_scene(self, scene_id: str) -> None:
        if self._scenes is not None:
            self._scenes.activate(scene_id)

    def _clear_scene(self) -> None:
        if self._scenes is not None:
            self._scenes.clear()

    def _toggle_focus_scene(self) -> None:
        if self._scenes is None:
            return
        if self._scenes.active_id == SCENE_FOCUS:
            self._scenes.clear()
        else:
            self._scenes.activate(SCENE_FOCUS)

    def _scene_menu_entries(self) -> tuple[SceneMenuEntry, ...]:
        if self._scenes is None:
            return ()
        active = self._scenes.active_id
        return tuple(
            SceneMenuEntry(id=scene.id, name=scene.name, active=scene.id == active)
            for scene in self._scenes.scenes
        )

    def _toggle_microphone(self) -> None:
        if self._microphone is not None:
            self._microphone.toggle()
            self._refresh_menu()

    def _toggle_dnd(self) -> None:
        if self._dnd is not None:
            self._dnd.toggle()
            self._refresh_menu()

    def _toggle_dark_mode(self) -> None:
        if self._dark_mode is not None:
            self._dark_mode.toggle()
            self._refresh_menu()

    def _setup_auto_quit(self) -> None:
        source = self._create_window_source()
        if source is None:
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

    def _create_window_source(self) -> WindowSource | None:
        """Pick the X11 or Wayland-extension window source, or none if neither."""
        kind = choose_window_source(
            has_x11=self._capabilities.has(SESSION_X11),
            has_wayland_source=self._capabilities.has(WAYLAND_WINDOW_SOURCE),
        )
        try:
            if kind == SOURCE_X11:
                from ..services.auto_quit.wnck_source import WnckWindowSource

                return WnckWindowSource()
            if kind == SOURCE_WAYLAND:
                from ..services.auto_quit.shell_extension_source import (
                    ShellExtensionWindowSource,
                )

                return ShellExtensionWindowSource()
        except Exception as error:
            log.warning("auto-quit window source unavailable", extra={"error": str(error)})
            return None
        return None

    def _setup_hotkey(self) -> None:
        if not self._capabilities.has(GLOBAL_SHORTCUTS):
            return
        try:
            from ..services.hotkey.portal import PortalGlobalShortcuts

            shortcuts = PortalGlobalShortcuts()
        except Exception as error:
            log.warning("global shortcuts unavailable", extra={"error": str(error)})
            return
        self._hotkey = HotkeyManager(shortcuts, self._hotkey_bindings())
        self._hotkey.start()

    def _hotkey_bindings(self) -> list[HotkeyBinding]:
        return [
            HotkeyBinding(
                KEEP_AWAKE_SHORTCUT_ID,
                KEEP_AWAKE_SHORTCUT_DESCRIPTION,
                self._toggle_keep_awake,
                lambda: self.config.get_bool("hotkey-enabled"),
            ),
            HotkeyBinding(
                SHELF_SHORTCUT_ID,
                SHELF_SHORTCUT_DESCRIPTION,
                self._open_shelf,
                lambda: self.config.get_bool("hotkey-shelf-enabled"),
            ),
            HotkeyBinding(
                CLIPBOARD_SHORTCUT_ID,
                CLIPBOARD_SHORTCUT_DESCRIPTION,
                self._open_clipboard,
                lambda: self.config.get_bool("hotkey-clipboard-enabled"),
            ),
            HotkeyBinding(
                FOCUS_SCENE_SHORTCUT_ID,
                FOCUS_SCENE_SHORTCUT_DESCRIPTION,
                self._toggle_focus_scene,
                lambda: self.config.get_bool("hotkey-focus-scene-enabled"),
            ),
        ]

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

    def _reconcile_clipboard(self) -> None:
        enabled = self.config.get_bool("clipboard-enabled")
        if enabled and self._clipboard is None:
            self._clipboard = ClipboardService(CLIPBOARD_DIR)
            self._clipboard.load()
            monitor = ClipboardMonitor(on_text=self._on_clipboard_text)
            if monitor.start():
                self._clipboard_monitor = monitor
        if self._tray is not None:
            self._tray.set_menu(self._build_menu())

    def _open_clipboard(self) -> None:
        if self._clipboard is None:
            self._clipboard = ClipboardService(CLIPBOARD_DIR)
            self._clipboard.load()
        from ..ui.clipboard.clipboard_window import ClipboardWindow

        if self._clipboard_window is None:
            self._clipboard_window = ClipboardWindow(self._clipboard, self._copy_to_clipboard)
            self._clipboard_window.connect("close-request", self._on_clipboard_closed)
        self._clipboard_window.present()

    def _on_clipboard_text(self, text: str) -> None:
        if self._clipboard is not None:
            self._clipboard.capture(text)

    def _copy_to_clipboard(self, text: str) -> None:
        """Put a history entry back on the system clipboard."""
        display = Gdk.Display.get_default()
        if display is not None:
            display.get_clipboard().set(text)

    def _on_clipboard_closed(self, _window: Adw.Window) -> bool:
        self._clipboard_window = None
        return False

    def _update_tray_active(self) -> None:
        if self._monitor is None:
            return
        active = (
            any(self.config.metric_placement(m) != PLACEMENT_OFF for m in TRAY_METRICS)
            or self.config.show_device_batteries
        )
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

    def _menu_device_rows(self) -> tuple[str, ...]:
        """Peripheral battery lines for the menu, empty when the toggle is off."""
        if not self.config.show_device_batteries:
            return ()
        if self._monitor is None or self._monitor.latest is None:
            return ()
        return tuple(render_device_rows(self._monitor.latest))

    def _on_snapshot(self, _monitor: SystemMonitor, snapshot: SystemSnapshot) -> None:
        self._refresh_tray_label()
        self._history.record(snapshot)
        self._evaluate_alerts(snapshot)
        if self._panel is not None:
            self._panel.update_snapshot(snapshot)
            self._panel.update_history(self._history)
            self._panel.update_processes(self._process_usage.top_cpu(PANEL_PROCESS_COUNT))
            self._update_net_processes()

    def _update_net_processes(self) -> None:
        """Refresh the panel's per-process network rows from a fresh ``ss`` read."""
        if self._panel is None or self._net_sampler is None:
            return
        rates = self._net_tracker.update(
            self._net_sampler.sample(), self.config.monitor_interval_seconds
        )
        self._panel.update_net_processes(top_by_throughput(rates, NET_PROCESS_COUNT))

    def _graph_metrics(self) -> frozenset[str]:
        """Metrics whose sparkline is enabled in settings (``monitor-graph-*``)."""
        return frozenset(
            metric for metric in GRAPH_METRICS if self.config.get_bool(f"monitor-graph-{metric}")
        )

    def _refresh_menu(self) -> None:
        if self._tray is not None:
            self._tray.set_menu(self._build_menu())

    def _on_menu_about_to_show(self) -> bool:
        """Rebuild the menu with fresh metric values just before it opens.

        Returning ``True`` only when metrics live in the dropdown lets the host
        re-read the layout on demand instead of us churning it on every sample.
        """
        if (
            not self._has_menu_metrics()
            and not self._has_quick_toggles()
            and not self.config.show_device_batteries
        ):
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
        if key.startswith("clipboard-"):
            self._reconcile_clipboard()
        if key.startswith("alert-"):
            self._reconcile_alerting()
        if key.startswith("monitor-graph-") and self._panel is not None:
            self._panel.set_graph_metrics(self._graph_metrics())
            self._panel.update_history(self._history)

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
            toggle_microphone=self._toggle_microphone,
            toggle_dnd=self._toggle_dnd,
            toggle_dark_mode=self._toggle_dark_mode,
            open_panel=self._open_panel,
            open_shelf=self._open_shelf,
            open_clipboard=self._open_clipboard,
            open_uninstaller=self._open_uninstaller,
            open_settings=self._open_settings,
            open_github=self._open_github,
            quit=self.quit,
            activate_scene=self._activate_scene,
            clear_scene=self._clear_scene,
        )

    def _build_menu(self) -> MenuModel:
        keep_awake_on = self._keep_awake is not None and self._keep_awake.is_active
        items = build_menu_items(
            self._menu_metric_values(),
            device_rows=self._menu_device_rows(),
            keep_awake_on=keep_awake_on,
            shelf_enabled=self.config.get_bool("shelf-enabled"),
            clipboard_enabled=self.config.get_bool("clipboard-enabled"),
            toggles=self._quick_toggle_state(),
            actions=self._menu_actions(),
            scenes=self._scene_menu_entries(),
        )
        return MenuModel(items)

    def _open_panel(self) -> None:
        from ..ui.panel.panel_window import PanelWindow

        if self._panel is None:
            self._panel = PanelWindow()
            self._panel.connect("close-request", self._on_panel_closed)
            self._panel.bind_process_actions(self._confirm_kill_process)
            if self._mixer is not None:
                self._panel.bind_mixer(self._mixer)
            else:
                self._panel.set_mixer_unavailable()
            if self._device_switcher is not None:
                self._panel.bind_devices(self._device_switcher)
        self._panel.set_temperature_unit(self.config.temperature_unit)
        self._panel.set_show_fans(self.config.get_bool("monitor-show-fan-control-beta"))
        self._panel.set_graph_metrics(self._graph_metrics())
        if self._device_switcher is not None:
            self._device_switcher.refresh()
        if self._monitor is not None:
            self._monitor.set_panel_open(True)
            if self._monitor.latest is not None:
                self._panel.update_snapshot(self._monitor.latest)
                self._panel.update_history(self._history)
                self._panel.update_processes(self._process_usage.top_cpu(PANEL_PROCESS_COUNT))
                self._update_net_processes()
        self._panel.present()

    def _confirm_kill_process(self, pid: int, name: str) -> None:
        """Ask before killing; a stray click should not terminate a process."""
        dialog = Adw.MessageDialog(
            transient_for=self._panel,
            heading=_("End process?"),
            body=_("Send a termination signal to “{name}” (PID {pid})?").format(name=name, pid=pid),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("end", _("End process"))
        dialog.set_response_appearance("end", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_kill_response, pid)
        dialog.present()

    def _on_kill_response(self, _dialog: Adw.MessageDialog, response: str, pid: int) -> None:
        if response == "end":
            self._process_killer.terminate(pid)

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

    def _open_github(self) -> None:
        """Open the author's GitHub profile from the tray menu credit row."""
        try:
            Gio.AppInfo.launch_default_for_uri(AUTHOR_GITHUB_URL, None)
        except GLib.Error:
            log.exception("Failed to open author GitHub profile")

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
