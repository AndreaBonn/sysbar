"""First-run welcome.

Replaces the macOS TCC permission flow with a capability check, and answers the
three things a new user does not know yet: where Sysbar is, how to reach it,
and what to turn on first. What the capabilities mean in plain words is decided
in :mod:`sysbar.app.onboarding_content`; this window only lays it out.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

from ...app.onboarding_content import (  # noqa: E402
    CapabilityReport,
    describe_capabilities,
    set_top_bar_metrics,
    top_bar_metrics_shown,
    tray_icon_blocked,
)
from ...core.capabilities import Capabilities  # noqa: E402
from ...core.config import Config  # noqa: E402
from ...core.constants import TRAY_ICON_NAME  # noqa: E402
from ...core.i18n import _  # noqa: E402
from ...services.autostart import AutostartManager  # noqa: E402

log = logging.getLogger(__name__)

_WINDOW_WIDTH = 480
_WINDOW_HEIGHT = 700
_UNAVAILABLE_ICON = "action-unavailable-symbolic"
_STEPS = (
    (
        TRAY_ICON_NAME,
        "Find the Sysbar icon in the top bar",
        "Next to the clock. It can show live values such as CPU and memory.",
    ),
    (
        "input-mouse-symbolic",
        "Click it for the live panel",
        "CPU, memory, network, battery and the busiest apps.",
    ),
    (
        "open-menu-symbolic",
        "Right-click for quick actions",
        "Keep awake, microphone, Do Not Disturb, scenes and every window.",
    ),
)


class OnboardingWindow(Adw.Window):
    """A single-page welcome: how to use Sysbar, what to start with, what works here."""

    def __init__(
        self,
        capabilities: Capabilities,
        *,
        config: Config,
        autostart: AutostartManager,
        on_finish: Callable[[], None],
    ) -> None:
        super().__init__(title=_("Welcome to Sysbar"))
        self.set_default_size(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self._config = config
        self._autostart = autostart
        self._on_finish = on_finish
        state = capabilities.snapshot()

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        if tray_icon_blocked(state):
            toolbar.add_top_bar(_tray_warning())

        page = Adw.PreferencesPage()
        page.add(_intro_group())
        page.add(_steps_group())
        page.add(self._starter_group())
        for group in _capability_groups(describe_capabilities(state)):
            page.add(group)
        toolbar.set_content(page)
        toolbar.add_bottom_bar(self._finish_bar())
        self.set_content(toolbar)

    def _starter_group(self) -> Adw.PreferencesGroup:
        """O2: the few switches worth deciding now; everything else waits in Preferences."""
        group = Adw.PreferencesGroup(
            title=_("Start with"), description=_("You can change these later in Preferences")
        )
        metrics = Adw.SwitchRow(title=_("Show CPU and memory in the top bar"))
        metrics.set_active(top_bar_metrics_shown(self._config))
        metrics.connect(
            "notify::active",
            lambda row, _p: set_top_bar_metrics(self._config, shown=row.get_active()),
        )
        group.add(metrics)
        settings = self._config.settings
        for key, title, subtitle in (
            ("clipboard-enabled", "Clipboard history", "Find again anything you copied"),
            ("shelf-enabled", "Shelf", "A drop zone for files you need in a moment"),
        ):
            row = Adw.SwitchRow(title=_(title), subtitle=_(subtitle))
            settings.bind(key, row, "active", Gio.SettingsBindFlags.DEFAULT)
            group.add(row)
        login = Adw.SwitchRow(title=_("Start at login"), active=self._autostart.is_enabled())
        login.connect(
            "notify::active", lambda row, _p: self._autostart.set_enabled(row.get_active())
        )
        group.add(login)
        return group

    def _on_login_toggled(self, row: Adw.SwitchRow, _param: object) -> None:
        try:
            self._autostart.set_enabled(row.get_active())
        except OSError:
            log.exception("could not change start at login")
            row.set_active(self._autostart.is_enabled())

    def _finish_bar(self) -> Gtk.Widget:
        finish = Gtk.Button(label=_("Get started"), css_classes=["suggested-action", "pill"])
        finish.connect("clicked", self._finish)
        bottom = Gtk.Box(halign=Gtk.Align.CENTER, margin_top=12, margin_bottom=16)
        bottom.append(finish)
        return bottom

    def _finish(self, _button: Gtk.Button) -> None:
        self._on_finish()
        self.close()


def _tray_warning() -> Adw.Banner:
    """O4: without a tray host Sysbar is invisible, so say it before anything else."""
    return Adw.Banner(
        title=_(
            "The top-bar icon cannot appear on this desktop, so Sysbar would stay "
            "invisible. Turn on the “AppIndicator and KStatusNotifierItem Support” "
            "extension in the Extensions app, then log in again."
        ),
        revealed=True,
    )


def _intro_group() -> Adw.PreferencesGroup:
    return Adw.PreferencesGroup(
        title=_("Welcome"),
        description=_(
            "Sysbar lives in the top bar, next to the clock. Choose below what to "
            "start with; everything can be changed later in Preferences."
        ),
    )


def _steps_group() -> Adw.PreferencesGroup:
    group = Adw.PreferencesGroup(title=_("How it works"))
    for icon, title, subtitle in _STEPS:
        row = Adw.ActionRow(title=_(title), subtitle=_(subtitle))
        row.add_prefix(Gtk.Image(icon_name=icon))
        group.add(row)
    return group


def _capability_groups(report: CapabilityReport) -> list[Adw.PreferencesGroup]:
    """O3: one line of what works, then each missing feature with its remedy."""
    groups = [
        Adw.PreferencesGroup(
            title=_("Ready on this computer"),
            description=", ".join(report.ready) if report.ready else _("Nothing detected yet"),
        )
    ]
    if report.missing:
        missing = Adw.PreferencesGroup(title=_("Not available here"))
        for item in report.missing:
            row = Adw.ActionRow(title=item.title, subtitle=item.hint, subtitle_selectable=True)
            row.add_suffix(Gtk.Image(icon_name=_UNAVAILABLE_ICON))
            missing.add(row)
        groups.append(missing)
    return groups
