"""Application life cycle and composition root.

A single-instance ``Adw.Application`` with no main window: Sysbar lives in the
tray. This module wires things together and owns nothing of its own beyond the
settings window and the onboarding; each feature's services, capability gating
and windows belong to its module under :mod:`sysbar.app.features`, and the tray
item belongs to :mod:`sysbar.app.tray_controller`.

Keeping it that way is a rule, not an accident: a feature added here should cost
its own module plus two lines, one in :meth:`SysbarApplication._build_features`
and one in :meth:`SysbarApplication._on_settings_changed`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib  # noqa: E402

from ..core.branding import register_app_icons  # noqa: E402
from ..core.capabilities import Capabilities  # noqa: E402
from ..core.config import Config  # noqa: E402
from ..core.constants import (  # noqa: E402
    APP_ID,
    CAPABILITY_REFRESH_INTERVAL_SECONDS,
    CURRENT_FEATURE_SET,
)
from ..core.localization import install_language  # noqa: E402
from ..services.autostart import AutostartManager  # noqa: E402
from ..services.hotkey.manager import HotkeyBinding  # noqa: E402
from ..services.notifier import Notifier  # noqa: E402
from ..services.palette.models import PaletteEntry  # noqa: E402
from ..services.system_monitor.snapshot import SystemSnapshot  # noqa: E402
from . import tray_state  # noqa: E402
from .commands.actions import CommandHandlers, install_actions, refresh_enabled  # noqa: E402
from .commands.models import CommandId  # noqa: E402
from .commands.wiring import build_handlers, current_state  # noqa: E402
from .context import AppContext  # noqa: E402
from .features import Features  # noqa: E402
from .features.audio import AudioFeature  # noqa: E402
from .features.auto_quit import AutoQuitFeature  # noqa: E402
from .features.clipboard import ClipboardFeature  # noqa: E402
from .features.hotkeys import HotkeyFeature  # noqa: E402
from .features.keep_awake import KeepAwakeFeature  # noqa: E402
from .features.monitor import MonitorFeature  # noqa: E402
from .features.palette import PaletteFeature  # noqa: E402
from .features.panel import PanelFeature  # noqa: E402
from .features.scenes import SceneDrivers, ScenesFeature  # noqa: E402
from .features.shelf import ShelfFeature  # noqa: E402
from .features.toggles import TogglesFeature  # noqa: E402
from .features.uninstaller import UninstallerFeature  # noqa: E402
from .features.updates import UpdateCheckFeature  # noqa: E402
from .palette_entries import collect  # noqa: E402
from .shortcuts import ShortcutTargets, build_hotkey_bindings  # noqa: E402
from .tray.menu_builder import MenuActions  # noqa: E402
from .tray_controller import TrayController, open_author_profile  # noqa: E402
from .windows import WindowSlot  # noqa: E402

if TYPE_CHECKING:
    from ..ui.settings.settings_window import SettingsWindow

log = logging.getLogger(__name__)


class SysbarApplication(Adw.Application):
    """Top-level application object."""

    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self._config: Config | None = None
        self._features: Features | None = None
        self._tray: TrayController | None = None
        self._hotkeys: HotkeyFeature | None = None
        self._capabilities = Capabilities()
        self._autostart = AutostartManager()
        self._actions: dict[CommandId, Gio.SimpleAction] = {}
        self._settings: WindowSlot[SettingsWindow] = WindowSlot(self._build_settings)
        self._held = False

    # --- life cycle -------------------------------------------------------

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        register_app_icons(Gdk.Display.get_default())
        self._config = Config()
        self._config.migrate_legacy_placements()
        install_language(self._config.get_string("app-language"))
        self._capabilities.refresh()
        context = self._build_context(self._config)
        self._features = self._build_features(context)
        self._install_actions()
        self._start(context)
        GLib.timeout_add_seconds(CAPABILITY_REFRESH_INTERVAL_SECONDS, self._refresh_capabilities)
        log.info("application started", extra={"capabilities": self._capabilities.snapshot()})

    def _build_context(self, config: Config) -> AppContext:
        return AppContext(
            config=config,
            capabilities=self._capabilities,
            notifier=Notifier(self),
            autostart=self._autostart,
        )

    def _build_features(self, context: AppContext) -> Features:
        """Construct every feature. Order matters only where one drives another."""
        keep_awake = KeepAwakeFeature(context, self._on_keep_awake_changed, self._refresh_label)
        toggles = TogglesFeature(context, self._refresh_menu)
        monitor = MonitorFeature(context, self._on_snapshot)
        audio = AudioFeature(context)
        return Features(
            monitor=monitor,
            keep_awake=keep_awake,
            audio=audio,
            panel=PanelFeature(context, monitor, audio),
            palette=PaletteFeature(self._palette_entries),
            toggles=toggles,
            scenes=ScenesFeature(
                context, SceneDrivers(keep_awake, toggles, audio), self._refresh_menu
            ),
            shelf=ShelfFeature(context),
            clipboard=ClipboardFeature(context),
            auto_quit=AutoQuitFeature(context),
            uninstaller=UninstallerFeature(context),
            updates=UpdateCheckFeature(context),
        )

    def _start(self, context: AppContext) -> None:
        """Publish the tray and kick off everything that runs once wired."""
        features = self.features
        self._tray = TrayController(context, features, self._menu_actions())
        self._tray.register(self.get_dbus_connection())
        context.config.settings.connect("changed", self._on_settings_changed)
        features.monitor.reconcile_alerting()
        features.shelf.reconcile()
        features.clipboard.reconcile()
        features.updates.start()
        self._hotkeys = HotkeyFeature(context, self._hotkey_bindings())
        self._tray.sync_sampling()

    def do_activate(self) -> None:
        if not self._held:
            self._held = True
            self.hold()
            if not self.config.get_bool("has-onboarded"):
                self._show_onboarding()
        else:
            self._open_panel()

    @property
    def capabilities(self) -> Capabilities:
        return self._capabilities

    @property
    def config(self) -> Config:
        if self._config is None:
            self._config = Config()
        return self._config

    @property
    def features(self) -> Features:
        """The wired features. Reaching them before startup is a wiring bug."""
        if self._features is None:
            raise RuntimeError("features are wired in do_startup")
        return self._features

    def _refresh_capabilities(self) -> bool:
        self._capabilities.refresh()
        return True

    # --- actions and shortcuts -------------------------------------------

    def _command_handlers(self) -> CommandHandlers:
        """Rebuilt on demand: it is a dict of bound methods, cheap to make."""
        return build_handlers(self.features, self._open_settings, self.quit)

    def _palette_entries(self) -> list[PaletteEntry]:
        """Read the features as they are now; the palette caches nothing."""
        return collect(self.features, self._command_handlers())

    def _install_actions(self) -> None:
        """Publish the whole catalogue on the bus, disabling what is unavailable."""
        self._actions = install_actions(
            self, self._command_handlers(), current_state(self.features)
        )

    def _refresh_action_state(self) -> None:
        refresh_enabled(self._actions, current_state(self.features))

    def _menu_actions(self) -> MenuActions:
        features = self.features
        return MenuActions(
            toggle_keep_awake=self._toggle_keep_awake,
            toggle_microphone=features.toggles.toggle_microphone,
            toggle_dnd=features.toggles.toggle_do_not_disturb,
            toggle_dark_mode=features.toggles.toggle_dark_mode,
            open_panel=self._open_panel,
            open_shelf=self._open_shelf,
            open_clipboard=self._open_clipboard,
            open_uninstaller=self._open_uninstaller,
            open_settings=self._open_settings,
            open_github=open_author_profile,
            quit=self.quit,
            activate_scene=features.scenes.activate,
            clear_scene=features.scenes.clear,
        )

    def _hotkey_bindings(self) -> list[HotkeyBinding]:
        return build_hotkey_bindings(
            self.config,
            ShortcutTargets(
                toggle_keep_awake=self._toggle_keep_awake,
                open_shelf=self._open_shelf,
                open_clipboard=self._open_clipboard,
                toggle_focus_scene=self.features.scenes.toggle_focus,
                open_palette=self.features.palette.open,
            ),
        )

    def _toggle_keep_awake(self) -> None:
        self.features.keep_awake.toggle()

    def _open_panel(self) -> None:
        self.features.panel.open()

    def _open_shelf(self) -> None:
        self.features.shelf.open()

    def _open_clipboard(self) -> None:
        self.features.clipboard.open()

    def _open_uninstaller(self) -> None:
        self.features.uninstaller.open()

    # --- signal routing ---------------------------------------------------

    def _refresh_menu(self) -> None:
        if self._tray is not None:
            self._tray.refresh_menu()

    def _refresh_label(self) -> None:
        if self._tray is not None:
            self._tray.refresh_label()

    def _on_snapshot(self, snapshot: SystemSnapshot) -> None:
        self._refresh_label()
        self.features.panel.push_snapshot(snapshot)
        self.features.scenes.note_snapshot(bool(snapshot.on_battery), snapshot.battery_percent)

    def _on_keep_awake_changed(self) -> None:
        self._refresh_menu()
        self._refresh_label()

    def _on_settings_changed(self, _settings: Gio.Settings, key: str) -> None:
        if self._tray is not None:
            self._tray.sync_sampling()
        self._refresh_action_state()
        if key.startswith("shelf-"):
            self.features.shelf.reconcile()
        if key.startswith("clipboard-"):
            self.features.clipboard.reconcile()
        if key.startswith("alert-"):
            self.features.monitor.reconcile_alerting()
        if key.startswith("monitor-graph-"):
            self.features.panel.apply_graph_metrics()

    # --- settings window and onboarding -----------------------------------

    def _build_settings(self) -> SettingsWindow:
        # Availability is frozen at build time. The window is rebuilt on every
        # open (close clears the slot), so a hardware change is picked up on the
        # next open rather than live in an already-open window.
        from ..ui.settings.settings_window import SettingsWindow

        return SettingsWindow(
            self.config,
            self._autostart,
            tray_state.unavailable_metrics(self.features.monitor.latest),
        )

    def _open_settings(self) -> None:
        self._settings.present()

    def _show_onboarding(self) -> None:
        from ..ui.onboarding.onboarding_window import OnboardingWindow

        window = OnboardingWindow(self._capabilities, on_finish=self._finish_onboarding)
        window.present()

    def _finish_onboarding(self) -> None:
        self.config.set_bool("has-onboarded", True)
        self.config.settings.set_int("features-onboarding-version", CURRENT_FEATURE_SET)
