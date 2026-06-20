"""Reusable settings rows bound to GSettings.

Titles, subtitles and option labels are passed as English source strings and
translated here via :func:`sysbar.core.i18n._`, so callers stay declarative.
"""

from __future__ import annotations

from collections.abc import Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

from ...core.i18n import _  # noqa: E402


def bound_switch(settings: Gio.Settings, key: str, title: str, subtitle: str = "") -> Adw.SwitchRow:
    """A switch row whose state is two-way bound to a boolean GSettings key."""
    row = Adw.SwitchRow(title=_(title))
    if subtitle:
        row.set_subtitle(_(subtitle))
    settings.bind(key, row, "active", Gio.SettingsBindFlags.DEFAULT)
    return row


def bound_spin(
    settings: Gio.Settings,
    key: str,
    title: str,
    lower: int,
    upper: int,
    subtitle: str = "",
) -> Adw.SpinRow:
    """A spin row over an integer GSettings key, clamped to ``[lower, upper]``."""
    adjustment = Gtk.Adjustment(lower=lower, upper=upper, step_increment=1, page_increment=10)
    row = Adw.SpinRow(title=_(title), adjustment=adjustment)
    if subtitle:
        row.set_subtitle(_(subtitle))
    row.set_value(settings.get_int(key))
    row.connect("notify::value", lambda spin, _param: settings.set_int(key, int(spin.get_value())))
    return row


class ComboBinding:
    """An ``Adw.ComboRow`` bound to a string or integer GSettings key."""

    def __init__(
        self,
        settings: Gio.Settings,
        key: str,
        title: str,
        options: Sequence[tuple[object, str]],
        is_int: bool,
    ) -> None:
        self._settings = settings
        self._key = key
        self._is_int = is_int
        self._values = [value for value, _label in options]

        labels = Gtk.StringList()
        for _value, label in options:
            labels.append(_(label))
        self.row = Adw.ComboRow(title=_(title), model=labels)
        self.row.set_selected(self._current_index())
        self.row.connect("notify::selected", self._on_selected)

    def _current_index(self) -> int:
        current: object = (
            self._settings.get_int(self._key)
            if self._is_int
            else self._settings.get_string(self._key)
        )
        try:
            return self._values.index(current)
        except ValueError:
            return 0

    def _on_selected(self, row: Adw.ComboRow, _param: object) -> None:
        value = self._values[row.get_selected()]
        if self._is_int:
            self._settings.set_int(self._key, int(value))
        else:
            self._settings.set_string(self._key, str(value))
