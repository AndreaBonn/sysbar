"""Preferences > Alerts: one switch per alert, with its limit already filled in.

I4 replaces "0 turns an alert off" with a switch that sets a sensible limit
when it turns on; the limit is adjustable inside the row. While alerts are
disabled as a whole, the individual rows are greyed out instead of looking live.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio  # noqa: E402

from ...app.settings_content import (  # noqa: E402
    ALERTS,
    CPU_SECONDS_KEY,
    AlertSpec,
    alert_subtitle,
    threshold_on_switch,
)
from ...core.i18n import _  # noqa: E402
from .widgets import bound_spin, bound_switch  # noqa: E402

_MASTER_KEY = "alert-enabled"
_MIN_THRESHOLD = 1
_MAX_CPU_SECONDS = 3600


class AlertsPage(Adw.PreferencesPage):
    """Master switch, then one expandable row per alert."""

    def __init__(self, settings: Gio.Settings) -> None:
        super().__init__(title=_("Alerts"), icon_name="dialog-warning-symbolic")
        self._settings = settings
        master = Adw.PreferencesGroup(
            title=_("Threshold alerts"),
            description=_("Get a notification when something needs your attention."),
        )
        master.add(bound_switch(settings, _MASTER_KEY, "Enable alerts"))
        self.add(master)
        alerts = Adw.PreferencesGroup()
        settings.bind(_MASTER_KEY, alerts, "sensitive", Gio.SettingsBindFlags.GET)
        self._limits: dict[str, Adw.SpinRow] = {}
        self._rows = [(spec, self._alert_row(spec)) for spec in ALERTS]
        for _spec, row in self._rows:
            alerts.add(row)
        self.add(alerts)
        self._handler = settings.connect("changed", self._on_changed)

    def disconnect_settings(self) -> None:
        self._settings.disconnect(self._handler)

    def _alert_row(self, spec: AlertSpec) -> Adw.ExpanderRow:
        row = Adw.ExpanderRow(title=_(spec.title), show_enable_switch=True)
        row.set_enable_expansion(self._settings.get_int(spec.key) > 0)
        row.connect("notify::enable-expansion", self._on_switched, spec)
        limit = bound_spin(self._settings, spec.key, "Limit", _MIN_THRESHOLD, spec.upper)
        self._limits[spec.key] = limit
        row.add_row(limit)
        if spec.sustained:
            row.add_row(
                bound_spin(
                    self._settings, CPU_SECONDS_KEY, "For at least (seconds)", 0, _MAX_CPU_SECONDS
                )
            )
        self._update_subtitle(spec, row)
        return row

    def _on_switched(self, row: Adw.ExpanderRow, _param: object, spec: AlertSpec) -> None:
        threshold = threshold_on_switch(
            spec=spec,
            enabled=row.get_enable_expansion(),
            current=self._settings.get_int(spec.key),
        )
        if threshold is not None:
            self._settings.set_int(spec.key, threshold)

    def _on_changed(self, _settings: Gio.Settings, key: str) -> None:
        for spec, row in self._rows:
            if key in (spec.key, CPU_SECONDS_KEY):
                value = self._settings.get_int(spec.key)
                row.set_enable_expansion(value > 0)
                if value >= _MIN_THRESHOLD:
                    # The spin read the store once; keep it on the value just written.
                    self._limits[spec.key].set_value(value)
                self._update_subtitle(spec, row)

    def _update_subtitle(self, spec: AlertSpec, row: Adw.ExpanderRow) -> None:
        value = self._settings.get_int(spec.key)
        cpu_seconds = self._settings.get_int(CPU_SECONDS_KEY)
        row.set_subtitle(alert_subtitle(spec, value, cpu_seconds=cpu_seconds))
