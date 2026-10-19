"""The System, Network and Power groups of the panel.

Each row puts its value on the right, large enough to read at a glance (P1),
with a level bar under percentage values so 61% reads as "a bit over half"
without knowing the machine (P2). Rows without data are hidden.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ...app.panel_summary import battery_text, memory_text  # noqa: E402
from ...core.constants import DEFAULT_TEMPERATURE_UNIT  # noqa: E402
from ...core.i18n import _  # noqa: E402
from ...services.metrics import metric_format as mf  # noqa: E402
from ...services.system_monitor.history import MetricHistory  # noqa: E402
from ...services.system_monitor.snapshot import SystemSnapshot  # noqa: E402
from .sparkline import Sparkline  # noqa: E402

_LEVEL_BAR_WIDTH = 72
_PERCENT_MAX = 100.0

# Maps a metric row key to the graphable metric whose sparkline it carries.
_ROW_SPARKLINE_METRIC = {
    "cpu": "cpu",
    "gpu": "gpu",
    "memory": "memory",
    "net_speed": "network",
    "battery": "battery",
    "power": "power",
}
# Rows whose value is a 0..100 percentage, and so get a level bar.
_LEVEL_ROWS = frozenset({"cpu", "gpu", "memory", "battery"})
_GROUPS = (
    (
        "System",
        (
            ("cpu", "CPU load"),
            ("cpu_temp", "CPU temperature"),
            ("gpu", "GPU"),
            ("memory", "Memory"),
            ("uptime", "Uptime"),
        ),
    ),
    ("Network", (("net_speed", "Speed"), ("net_total", "Total"))),
    ("Power", (("battery", "Battery"), ("power", "Power draw"))),
)


class _MetricRow:
    """One metric: title on the left, value (and optional level bar) on the right."""

    def __init__(self, key: str, title: str) -> None:
        self.row = Adw.ActionRow(title=_(title))
        self._value = Gtk.Label(css_classes=["heading", "numeric"], xalign=1.0)
        self._level: Gtk.LevelBar | None = None
        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
        column.append(self._value)
        if key in _LEVEL_ROWS:
            self._level = Gtk.LevelBar(max_value=_PERCENT_MAX, width_request=_LEVEL_BAR_WIDTH)
            # The default offsets colour a low value as a warning, which is wrong
            # for load (low is good) and right only for battery; stay neutral.
            for offset in ("low", "high", "full"):
                self._level.remove_offset_value(offset)
            column.append(self._level)
        self.row.add_suffix(column)

    def show(self, text: str | None, level: float | None) -> None:
        self.row.set_visible(text is not None)
        if text is None:
            return
        self._value.set_label(text)
        if self._level is not None and level is not None:
            self._level.set_value(min(max(level, 0.0), _PERCENT_MAX))


class MetricsSection(Gtk.Box):
    """The live metric groups, fed one snapshot at a time."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.temperature_unit = DEFAULT_TEMPERATURE_UNIT
        self._rows: dict[str, _MetricRow] = {}
        self._sparklines: dict[str, Sparkline] = {}
        self._graph_enabled: frozenset[str] = frozenset()
        for title, rows in _GROUPS:
            group = Adw.PreferencesGroup(title=_(title))
            for key, label in rows:
                row = _MetricRow(key, label)
                self._rows[key] = row
                self._attach_sparkline(key, row.row)
                group.add(row.row)
            self.append(group)

    def _attach_sparkline(self, key: str, row: Adw.ActionRow) -> None:
        metric = _ROW_SPARKLINE_METRIC.get(key)
        if metric is None:
            return
        sparkline = Sparkline()
        sparkline.set_visible(False)
        row.add_suffix(sparkline)
        self._sparklines[metric] = sparkline

    def set_graph_metrics(self, enabled: frozenset[str]) -> None:
        """Set which metrics show a sparkline; hides the rest immediately."""
        self._graph_enabled = enabled
        for metric, sparkline in self._sparklines.items():
            if metric not in enabled:
                sparkline.set_visible(False)

    def update_history(self, history: MetricHistory) -> None:
        """Refresh every enabled sparkline from the recorded history."""
        for metric, sparkline in self._sparklines.items():
            series = history.series(metric)
            visible = metric in self._graph_enabled and len(series) >= 2
            sparkline.set_visible(visible)
            if visible:
                sparkline.set_values(series)

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Refresh all metric rows; rows without data are hidden."""
        rows = self._rows
        rows["cpu"].show(_percent(snapshot.cpu_percent), snapshot.cpu_percent)
        rows["cpu_temp"].show(self._temp(snapshot.cpu_temp_celsius), None)
        rows["gpu"].show(_percent(snapshot.gpu_percent), snapshot.gpu_percent)
        rows["memory"].show(memory_text(snapshot), snapshot.memory_percent)
        rows["uptime"].show(_uptime(snapshot.uptime_seconds), None)
        rows["net_speed"].show(
            _net_pair(snapshot.net_rx_rate, snapshot.net_tx_rate, rate=True), None
        )
        rows["net_total"].show(
            _net_pair(snapshot.net_rx_total, snapshot.net_tx_total, rate=False), None
        )
        rows["battery"].show(battery_text(snapshot), snapshot.battery_percent)
        power = snapshot.power_watts
        rows["power"].show(f"{power:.0f} W" if power is not None else None, None)

    def _temp(self, celsius: float | None) -> str | None:
        if celsius is None:
            return None
        return mf.format_temperature(celsius, self.temperature_unit)


def _percent(value: float | None) -> str | None:
    return mf.format_percent(value) if value is not None else None


def _uptime(seconds: float | None) -> str | None:
    return mf.format_uptime(seconds) if seconds is not None else None


def _net_pair(rx: float | None, tx: float | None, *, rate: bool) -> str | None:
    if rx is None or tx is None:
        return None
    fmt = mf.format_rate if rate else mf.format_bytes
    return f"↓{fmt(rx)} ↑{fmt(tx)}"
