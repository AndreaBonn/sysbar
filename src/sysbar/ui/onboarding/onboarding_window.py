"""First-run onboarding.

Replaces the macOS TCC permission flow with a capability check: it shows which
features are available on this system before handing over to the tray.
"""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ...core.capabilities import Capabilities  # noqa: E402
from ...core.i18n import _  # noqa: E402
from ..footer import build_footer  # noqa: E402

_CAPABILITY_LABELS = {
    "session_x11": "X11 session (auto-quit, shelf shake)",
    "wayland_window_source": "Wayland auto-quit (Sysbar shell extension)",
    "global_shortcuts": "Global keep-awake hotkey",
    "appindicator": "Tray icon support",
    "sensors": "Temperature sensors",
    "pipewire_pulse": "Audio mixer and microphone toggle",
    "gnome_desktop": "Do-not-disturb and dark-mode toggles",
    "logind": "Keep awake",
    "upower": "Battery metrics",
    "polkit": "System uninstaller",
}


class OnboardingWindow(Adw.Window):
    """A single-page welcome listing detected capabilities."""

    def __init__(self, capabilities: Capabilities, on_finish: Callable[[], None]) -> None:
        super().__init__(title=_("Welcome to Sysbar"))
        self.set_default_size(440, 520)
        self._on_finish = on_finish

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        page = Adw.PreferencesPage()
        intro = Adw.PreferencesGroup(
            title=_("Welcome"),
            description="Sysbar runs in the tray. Every feature is off until you enable it.",
        )
        page.add(intro)

        detected = Adw.PreferencesGroup(title=_("Detected on this system"))
        state = capabilities.snapshot()
        for name, label in _CAPABILITY_LABELS.items():
            row = Adw.ActionRow(title=label)
            icon = "emblem-ok-symbolic" if state.get(name) else "action-unavailable-symbolic"
            row.add_suffix(Gtk.Image(icon_name=icon))
            detected.add(row)
        page.add(detected)

        toolbar.set_content(page)

        finish = Gtk.Button(label=_("Get started"), css_classes=["suggested-action"])
        finish.connect("clicked", self._finish)
        bottom = Gtk.Box(halign=Gtk.Align.CENTER, margin_top=8, margin_bottom=16)
        bottom.append(finish)
        toolbar.add_bottom_bar(bottom)
        toolbar.add_bottom_bar(build_footer())

        self.set_content(toolbar)

    def _finish(self, _button: Gtk.Button) -> None:
        self._on_finish()
        self.close()
