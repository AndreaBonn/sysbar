"""Pure text and level derivations behind the panel's metric rows.

The panel widgets only place these values; what a row says, and when it is
hidden, is decided here so it can be tested without GTK. Kept apart from
:mod:`sysbar.app.panel_summary`, which answers "is the machine fine?"; this
answers "what does each row read?".
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.i18n import _
from ..services.metrics import metric_format as mf
from ..services.system_monitor.processes import ProcessUsage
from ..services.system_monitor.snapshot import SystemSnapshot
from .panel_summary import battery_text, memory_text

PERCENT_MAX = 100.0


@dataclass(frozen=True)
class MetricRow:
    """What one metric row shows: its value text and its level-bar value.

    ``text`` is ``None`` when the row has no data and should be hidden.
    ``level`` is the raw 0..100 value for rows with a level bar, else ``None``.
    A hidden row ignores its level: memory can report a percentage while its
    text is unavailable, and the row then stays hidden rather than showing a
    bare bar.
    """

    text: str | None
    level: float | None = None


def clamp_level(level: float) -> float:
    """Clamp a level-bar value into ``0..PERCENT_MAX``."""
    return min(max(level, 0.0), PERCENT_MAX)


def net_pair(rx: float | None, tx: float | None, *, rate: bool) -> str | None:
    """The ``↓rx ↑tx`` pair, as rates (``rate=True``) or byte totals.

    ``None`` when either direction is unknown, so the row is hidden rather
    than half filled.
    """
    if rx is None or tx is None:
        return None
    fmt = mf.format_rate if rate else mf.format_bytes
    return f"↓{fmt(rx)} ↑{fmt(tx)}"


def _percent(value: float | None) -> str | None:
    return mf.format_percent(value) if value is not None else None


def _uptime(seconds: float | None) -> str | None:
    return mf.format_uptime(seconds) if seconds is not None else None


def _temperature(celsius: float | None, unit: str) -> str | None:
    return mf.format_temperature(celsius, unit) if celsius is not None else None


def _power(watts: float | None) -> str | None:
    return f"{watts:.0f} W" if watts is not None else None


def metric_rows(snapshot: SystemSnapshot, temperature_unit: str) -> dict[str, MetricRow]:
    """The value of every metric row for one snapshot, keyed by row key."""
    return {
        "cpu": MetricRow(_percent(snapshot.cpu_percent), snapshot.cpu_percent),
        "cpu_temp": MetricRow(_temperature(snapshot.cpu_temp_celsius, temperature_unit)),
        "gpu": MetricRow(_percent(snapshot.gpu_percent), snapshot.gpu_percent),
        "memory": MetricRow(memory_text(snapshot), snapshot.memory_percent),
        "uptime": MetricRow(_uptime(snapshot.uptime_seconds)),
        "net_speed": MetricRow(net_pair(snapshot.net_rx_rate, snapshot.net_tx_rate, rate=True)),
        "net_total": MetricRow(net_pair(snapshot.net_rx_total, snapshot.net_tx_total, rate=False)),
        "battery": MetricRow(battery_text(snapshot), snapshot.battery_percent),
        "power": MetricRow(_power(snapshot.power_watts)),
    }


def process_row_text(process: ProcessUsage) -> tuple[str, str]:
    """Title and subtitle of a top-process row; a nameless process reads "Unknown"."""
    cpu = mf.format_percent(process.cpu_percent)
    memory = mf.format_bytes(process.memory_bytes)
    return process.name or _("Unknown"), f"{cpu} CPU · {memory}"


def fan_subtitle(rpm: float) -> str:
    """A fan row's subtitle: the speed in whole RPM."""
    return f"{rpm:.0f} RPM"
