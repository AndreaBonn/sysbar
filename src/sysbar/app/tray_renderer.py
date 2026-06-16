"""Compose the short tray label from a snapshot (port of the macOS renderer).

Pure and unit-tested: given a snapshot and the user's opted-in metrics, it
returns the string shown next to the tray icon.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.constants import MEMORY_STYLE_BOTH, MEMORY_STYLE_DOT
from ..services.metrics import metric_format as mf
from ..services.system_monitor.snapshot import SystemSnapshot

_SEPARATOR = " · "
_PRESSURE_DOTS = {"normal": "●", "warning": "●", "critical": "●"}


@dataclass(frozen=True)
class TrayOptions:
    """The user's opted-in tray metrics and display preferences."""

    show_cpu: bool = False
    show_gpu: bool = False
    show_memory: bool = False
    show_network: bool = False
    show_battery: bool = False
    show_power: bool = False
    memory_style: str = "percent"
    temperature_unit: str = "celsius"


def render_tray_label(snapshot: SystemSnapshot, options: TrayOptions) -> str:
    """Return the tray label, joining opted-in non-empty metric segments."""
    segments: list[str] = []
    if options.show_cpu:
        segments.extend(_cpu_segments(snapshot, options.temperature_unit))
    if options.show_gpu and snapshot.gpu_percent is not None:
        segments.append(f"GPU {mf.format_percent(snapshot.gpu_percent)}")
    if options.show_memory:
        segments.extend(_memory_segments(snapshot, options.memory_style))
    if options.show_network:
        segments.extend(_network_segments(snapshot))
    if options.show_battery and snapshot.battery_percent is not None:
        segments.append(f"BAT {mf.format_percent(snapshot.battery_percent)}")
    if options.show_power and snapshot.power_watts is not None:
        segments.append(f"{snapshot.power_watts:.0f} W")
    return _SEPARATOR.join(segments)


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
