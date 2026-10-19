"""Preferences window: one page per feature, bound live to GSettings."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from ... import __version__  # noqa: E402
from ...core.branding import has_app_icon  # noqa: E402
from ...core.config import Config  # noqa: E402
from ...core.constants import APP_ICON_NAME, AUTHOR_GITHUB_URL, AUTHOR_NAME  # noqa: E402
from ...core.i18n import _  # noqa: E402
from ...core.localization import install_language  # noqa: E402
from ...services.autostart import AutostartManager  # noqa: E402
from .alerts_page import AlertsPage  # noqa: E402
from .features_page import FeaturesPage  # noqa: E402
from .monitor_page import MonitorPage  # noqa: E402
from .widgets import ComboBinding, bound_switch  # noqa: E402

log = logging.getLogger(__name__)

_LANGUAGE_KEY = "app-language"
_ABOUT_LOGO_PIXELS = 96

_LANGUAGES = [("", "System"), ("en", "English"), ("it", "Italiano")]
_DURATIONS = [(0, "Indefinite"), (15, "15 min"), (30, "30 min"), (60, "1 hour"), (120, "2 hours")]
_BATTERY_LIMITS = [(0, "Never"), (5, "5%"), (10, "10%"), (15, "15%"), (20, "20%")]


class SettingsWindow(Adw.PreferencesWindow):
    """Live-bound preferences, one page per feature."""

    def __init__(
        self,
        config: Config,
        autostart: AutostartManager,
        unavailable_metrics: frozenset[str] = frozenset(),
        *,
        on_show_onboarding: Callable[[], None],
        tray_preview: Callable[[], str | None] = lambda: None,
    ) -> None:
        super().__init__(title=_("Sysbar Preferences"))
        self.set_default_size(640, 560)
        self._config = config
        self._settings = config.settings
        self._autostart = autostart
        self._on_show_onboarding = on_show_onboarding
        self._combos: list[ComboBinding] = []

        self._monitor = MonitorPage(self._settings, unavailable_metrics, tray_preview)
        self._alerts = AlertsPage(self._settings)
        self._add_pages()

        self._language_handler = self._settings.connect(
            f"changed::{_LANGUAGE_KEY}", self._on_language_changed
        )
        self.connect("close-request", self._on_close_request)

    def _add_pages(self) -> None:
        """I1: what Sysbar can do comes first; housekeeping pages follow."""
        for page in (
            FeaturesPage(self._settings),
            self._general_page(),
            self._monitor,
            self._alerts,
            self._keep_awake_page(),
            self._about_page(),
        ):
            self.add(page)

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
        page.add(self._shortcuts_group())
        page.add(self._automation_group())
        return page

    def _shortcuts_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title=_("Global shortcuts"),
            description=_("Assign the keys from your desktop's keyboard settings"),
        )
        for key, title in (
            ("hotkey-enabled", "Toggle keep awake"),
            ("hotkey-focus-scene-enabled", "Toggle Focus scene"),
            ("hotkey-palette-enabled", "Open command palette"),
        ):
            group.add(bound_switch(self._settings, key, title))
        return group

    def _automation_group(self) -> Adw.PreferencesGroup:
        """Triggers are not a shortcut: they act without anyone pressing a key."""
        group = Adw.PreferencesGroup(
            title=_("Automation"),
            description=_("Let scene rules change the active scene on their own"),
        )
        group.add(
            bound_switch(
                self._settings,
                "scene-triggers-enabled",
                "Automatic scene triggers",
                "A scene you chose by hand is never replaced",
            )
        )
        return group

    def _keep_awake_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title=_("Keep Awake"), icon_name="weather-clear-symbolic")
        group = Adw.PreferencesGroup(title=_("Keep Awake"))
        group.add(self._combo("default-duration-minutes", "Default duration", _DURATIONS, True))
        group.add(self._combo("battery-limit-percent", "Stop below battery", _BATTERY_LIMITS, True))
        group.add(bound_switch(self._settings, "show-countdown", "Show countdown in tray"))
        group.add(bound_switch(self._settings, "clamshell-preferred", "Keep awake with lid closed"))
        page.add(group)
        return page

    def _about_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title=_("About"), icon_name="help-about-symbolic")

        if has_app_icon(Gdk.Display.get_default()):
            banner = Adw.PreferencesGroup()
            logo = Gtk.Image.new_from_icon_name(APP_ICON_NAME)
            logo.set_pixel_size(_ABOUT_LOGO_PIXELS)
            logo.set_margin_top(12)
            logo.set_margin_bottom(12)
            banner.add(logo)
            page.add(banner)

        group = Adw.PreferencesGroup(title=_("About"))
        group.add(Adw.ActionRow(title=_("Version"), subtitle=__version__))

        welcome_row = Adw.ActionRow(title=_("Show the welcome again"))
        button = Gtk.Button(label=_("Show now"), valign=Gtk.Align.CENTER)
        button.connect("clicked", lambda _button: self._on_show_onboarding())
        welcome_row.add_suffix(button)
        welcome_row.set_activatable_widget(button)
        group.add(welcome_row)
        group.add(_author_row())
        page.add(group)
        return page

    def _on_autostart_toggled(self, row: Adw.SwitchRow, _param: object) -> None:
        self._autostart.set_enabled(row.get_active())

    def _on_language_changed(self, settings: Gio.Settings, _key: str) -> None:
        """Reinstall the catalog and prompt for a restart (already-built UI stays as-is)."""
        install_language(settings.get_string(_LANGUAGE_KEY))
        self.add_toast(Adw.Toast(title=_("Restart Sysbar to apply the language")))

    def _on_close_request(self, _window: Adw.PreferencesWindow) -> bool:
        self._settings.disconnect(self._language_handler)
        self._monitor.disconnect_settings()
        self._alerts.disconnect_settings()
        return False


def _author_row() -> Adw.ActionRow:
    """S1: the credit lives here, once, instead of at the foot of every window."""
    row = Adw.ActionRow(
        title=_("Made by {name}").format(name=AUTHOR_NAME),
        subtitle=_("The author's profile on GitHub"),
        activatable=True,
    )
    row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
    row.connect("activated", lambda _row: _open_author_profile(row.get_root()))
    return row


def _open_author_profile(parent: Gtk.Window | None) -> None:
    launcher = Gtk.UriLauncher.new(AUTHOR_GITHUB_URL)
    launcher.launch(parent, None, _on_launched)


def _on_launched(launcher: Gtk.UriLauncher, result: Gio.AsyncResult) -> None:
    try:
        launcher.launch_finish(result)
    except GLib.Error:
        log.exception("could not open the author's profile")
