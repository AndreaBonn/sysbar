"""The system monitor snapshot.

Every field is optional: ``None`` means "not available on this hardware" and the
corresponding UI row hides itself (identical to the macOS original).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SystemSnapshot:
    """One sampling of all system metrics."""

    cpu_percent: float | None = None
    cpu_per_core: list[float] | None = None
    cpu_temp_celsius: float | None = None
    gpu_percent: float | None = None
    gpu_temp_celsius: float | None = None
    memory_percent: float | None = None
    memory_pressure: str | None = None
    disk_percent: float | None = None
    uptime_seconds: float | None = None
    net_rx_rate: float | None = None
    net_tx_rate: float | None = None
    net_rx_total: int | None = None
    net_tx_total: int | None = None
    battery_percent: float | None = None
    battery_charging: bool | None = None
    on_battery: bool | None = None
    power_watts: float | None = None
    temperatures: dict[str, float] = field(default_factory=dict)
    fans: dict[str, float] = field(default_factory=dict)
