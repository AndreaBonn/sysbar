"""Preferences > Features: what Sysbar can do, each with one line on what it does.

I2 gives every switch a subtitle; I6 gathers a feature's own options (shake to
open, its global shortcut) under it, in an expander that only opens while the
feature is on, instead of scattering them over two pages.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio  # noqa: E402

from ...app.settings_content import SHORTCUTS  # noqa: E402
from ...core.i18n import _  # noqa: E402
from .widgets import bound_switch  # noqa: E402

_SHORTCUT_KEYS = frozenset(shortcut.key for shortcut in SHORTCUTS)
_SIMPLE_FEATURES = (
    ("monitor-show-mixer", "Volume mixer", "Set the volume of each app from the panel"),
    (
        "auto-quit-enabled",
        "Auto-quit closed apps",
        "Quit an app when you close its last window",
    ),
)
# Feature key, title, subtitle, and its sub-options as (key, title, subtitle).
_EXPANDABLE_FEATURES = (
    (
        "shelf-enabled",
        "Shelf",
        "A drop zone for files, links and text you need in a moment",
        (
            ("shelf-shake-to-open", "Shake the mouse to open", "X11 sessions only"),
            ("hotkey-shelf-enabled", "Global shortcut", ""),
        ),
    ),
    (
        "clipboard-enabled",
        "Clipboard history",
        "Find again anything you copied",
        (("hotkey-clipboard-enabled", "Global shortcut", ""),),
    ),
)


class FeaturesPage(Adw.PreferencesPage):
    """One switch per feature, options nested under the feature they belong to."""

    def __init__(self, settings: Gio.Settings, *, shortcuts_available: bool = True) -> None:
        super().__init__(title=_("Features"), icon_name="view-grid-symbolic")
        group = Adw.PreferencesGroup(
            title=_("Features"),
            description=_("Pick what Sysbar does for you. You can change it any time."),
        )
        for key, title, subtitle in _SIMPLE_FEATURES:
            group.add(bound_switch(settings, key, title, subtitle))
        for key, title, subtitle, options in _EXPANDABLE_FEATURES:
            expander = Adw.ExpanderRow(
                title=_(title), subtitle=_(subtitle), show_enable_switch=True
            )
            settings.bind(key, expander, "enable-expansion", Gio.SettingsBindFlags.DEFAULT)
            for option_key, option_title, option_subtitle in options:
                row = bound_switch(settings, option_key, option_title, option_subtitle)
                if option_key in _SHORTCUT_KEYS and not shortcuts_available:
                    # I5: a switch that cannot work is shown as such, with where to look.
                    row.set_sensitive(False)
                    row.set_subtitle(_("Not offered by this desktop: see General"))
                expander.add_row(row)
            group.add(expander)
        self.add(group)
