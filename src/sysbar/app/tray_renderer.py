"""Compose tray output from a snapshot (port of the macOS renderer).

Pure and unit-tested. Each metric carries a placement (``off``, ``bar`` or
``menu``): :func:`render_tray_label` builds the always-visible label from the
``bar`` metrics, while :func:`render_menu_metrics` builds the read-only lines
shown in the dropdown for the ``menu`` metrics.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.constants import (
    MEMORY_STYLE_BOTH,
    MEMORY_STYLE_DOT,
    PLACEMENT_BAR,
    PLACEMENT_MENU,
    PLACEMENT_OFF,
    TRAY_METRICS,
)
from ..services.metrics import metric_format as mf
from ..services.system_monitor.snapshot import SystemSnapshot

_SEPARATOR = " · "
_PRESSURE_DOTS = {"normal": "●", "warning": "●", "critical": "●"}


@dataclass(frozen=True)
class TrayOptions:
    """Per-metric placement and display preferences for the tray."""

    cpu: str = PLACEMENT_OFF
    gpu: str = PLACEMENT_OFF
    memory: str = PLACEMENT_OFF
    network: str = PLACEMENT_OFF
    battery: str = PLACEMENT_OFF
    power: str = PLACEMENT_OFF
    memory_style: str = "percent"
    temperature_unit: str = "celsius"

    def placement(self, metric: str) -> str:
        """Return the placement string for a metric id (defaults to ``off``)."""
        return getattr(self, metric, PLACEMENT_OFF)


def render_tray_label(snapshot: SystemSnapshot, options: TrayOptions) -> str:
    """Return the always-visible label, joining the ``bar`` metric segments."""
    segments: list[str] = []
    for metric in TRAY_METRICS:
        if options.placement(metric) == PLACEMENT_BAR:
            segments.extend(_metric_segments(snapshot, metric, options))
    return _SEPARATOR.join(segments)


def render_menu_metrics(snapshot: SystemSnapshot, options: TrayOptions) -> list[str]:
    """Return one read-only line per ``menu`` metric that has data to show."""
    return list(menu_metric_values(snapshot, options).values())


def menu_metric_values(snapshot: SystemSnapshot, options: TrayOptions) -> dict[str, str]:
    """Map each ``menu`` metric id to its formatted line, skipping empty ones.

    Keys follow :data:`TRAY_METRICS` order so callers can fill fixed menu slots
    deterministically.
    """
    values: dict[str, str] = {}
    for metric in TRAY_METRICS:
        if options.placement(metric) != PLACEMENT_MENU:
            continue
        segments = _metric_segments(snapshot, metric, options)
        if segments:
            values[metric] = _SEPARATOR.join(segments)
    return values


def _metric_segments(snapshot: SystemSnapshot, metric: str, options: TrayOptions) -> list[str]:
    if metric == "cpu":
        return _cpu_segments(snapshot, options.temperature_unit)
    if metric == "gpu":
        if snapshot.gpu_percent is None:
            return []
        return [f"GPU {mf.format_percent(snapshot.gpu_percent)}"]
    if metric == "memory":
        return _memory_segments(snapshot, options.memory_style)
    if metric == "network":
        return _network_segments(snapshot)
    if metric == "battery":
        if snapshot.battery_percent is None:
            return []
        return [f"BAT {mf.format_percent(snapshot.battery_percent)}"]
    if metric == "power":
        if snapshot.power_watts is None:
            return []
        return [f"{snapshot.power_watts:.0f} W"]
    return []  # pragma: no cover - defensive: metric is always a TRAY_METRICS id


def _cpu_segments(snapshot: SystemSnapshot, unit: str) -> list[str]:
    segments: list[str] = []
    if snapshot.cpu_percent is not None:
        segments.append(f"CPU {mf.format_percent(snapshot.cpu_percent)}")
    if snapshot.cpu_temp_celsius is not None:
        segments.append(mf.format_temperature(snapshot.cpu_temp_celsius, unit))
    return segments


def _memory_segments(snapshot: SystemSnapshot, style: str) -> list[str]:
    if snapshot.memory_percent is None:
        return []
    percent = mf.format_percent(snapshot.memory_percent)
    if style == MEMORY_STYLE_DOT:
        return [_PRESSURE_DOTS.get(snapshot.memory_pressure or "normal", "●")]
    if style == MEMORY_STYLE_BOTH:
        dot = _PRESSURE_DOTS.get(snapshot.memory_pressure or "normal", "●")
        return [f"{dot} {percent}"]
    return [f"RAM {percent}"]


def _network_segments(snapshot: SystemSnapshot) -> list[str]:
    if snapshot.net_rx_rate is None or snapshot.net_tx_rate is None:
        return []
    return [f"↓{mf.format_rate(snapshot.net_rx_rate)} ↑{mf.format_rate(snapshot.net_tx_rate)}"]
