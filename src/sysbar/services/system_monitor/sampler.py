"""Stateful sampler that turns source readings into a :class:`SystemSnapshot`.

Holds the previous CPU and network counters so it can compute deltas. The first
snapshot has ``None`` rates/load (no baseline yet); subsequent ones are live.
This class is pure with respect to its injected readers and is unit-tested.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from . import parsers
from .parsers import CpuSample
from .ports import (
    DiskReader,
    GpuReader,
    PeripheralReader,
    PowerReader,
    ProcReader,
    SensorReader,
)
from .snapshot import SystemSnapshot

log = logging.getLogger(__name__)

_LOOPBACK = "lo"
_T = TypeVar("_T")


class SystemSampler:
    """Compute snapshots from injected readers, tracking deltas across calls."""

    def __init__(
        self,
        proc: ProcReader,
        sensors: SensorReader,
        gpu: GpuReader,
        power: PowerReader,
        disk: DiskReader,
        peripherals: PeripheralReader,
    ) -> None:
        self._proc = proc
        self._sensors = sensors
        self._gpu = gpu
        self._power = power
        self._disk = disk
        self._peripherals = peripherals
        self._prev_cpu: dict[str, CpuSample] = {}
        self._prev_net: dict[str, tuple[int, int]] = {}

    def build_snapshot(self, interval_seconds: float) -> SystemSnapshot:
        cpu_percent, cpu_per_core = self._cpu()
        net_rx_rate, net_tx_rate, rx_total, tx_total = self._network(interval_seconds)
        return SystemSnapshot(
            cpu_percent=cpu_percent,
            cpu_per_core=cpu_per_core,
            cpu_temp_celsius=self._safe(self._sensors.cpu_temperature),
            gpu_percent=self._safe(self._gpu.utilization),
            gpu_temp_celsius=self._safe(self._gpu.temperature),
            memory_percent=self._memory_percent(),
            memory_pressure=self._memory_pressure(),
            disk_percent=self._safe(self._disk.usage_percent),
            uptime_seconds=self._uptime(),
            net_rx_rate=net_rx_rate,
            net_tx_rate=net_tx_rate,
            net_rx_total=rx_total,
            net_tx_total=tx_total,
            battery_percent=self._safe(self._power.battery_percent),
            battery_charging=self._safe(self._power.charging),
            on_battery=self._safe(self._power.on_battery),
            power_watts=self._safe(self._power.power_watts),
            temperatures=self._temperatures(),
            fans=self._fans(),
            peripherals=self._peripherals.batteries(),
        )

    def _cpu(self) -> tuple[float | None, list[float] | None]:
        samples = parsers.parse_cpu_stat(self._proc.read_stat())
        previous = self._prev_cpu
        self._prev_cpu = samples
        if "cpu" not in previous or "cpu" not in samples:
            return None, None
        total = parsers.cpu_busy_percent(previous["cpu"], samples["cpu"])
        cores = [
            parsers.cpu_busy_percent(previous[name], samples[name])
            for name in sorted(samples)
            if name != "cpu" and name in previous
        ]
        return total, cores or None

    def _network(
        self, interval_seconds: float
    ) -> tuple[float | None, float | None, int | None, int | None]:
        counters = parsers.parse_net_dev(self._proc.read_net_dev())
        active = {name: value for name, value in counters.items() if name != _LOOPBACK}
        rx_total = sum(rx for rx, _ in active.values())
        tx_total = sum(tx for _, tx in active.values())
        previous = self._prev_net
        self._prev_net = active
        if not previous:
            return None, None, rx_total, tx_total
        prev_rx = sum(rx for rx, _ in previous.values())
        prev_tx = sum(tx for _, tx in previous.values())
        rx_rate = parsers.rate_per_second(prev_rx, rx_total, interval_seconds)
        tx_rate = parsers.rate_per_second(prev_tx, tx_total, interval_seconds)
        return rx_rate, tx_rate, rx_total, tx_total

    def _memory_percent(self) -> float | None:
        try:
            return parsers.memory_used_percent(parsers.parse_meminfo(self._proc.read_meminfo()))
        except (OSError, ValueError):
            return None

    def _memory_pressure(self) -> str | None:
        text = self._proc.read_psi_memory()
        if not text:
            return None
        avg10 = parsers.parse_psi_some_avg10(text)
        return parsers.memory_pressure_level(avg10) if avg10 is not None else None

    def _uptime(self) -> float | None:
        try:
            return parsers.parse_uptime(self._proc.read_uptime())
        except (OSError, ValueError, IndexError):
            return None

    def _temperatures(self) -> dict[str, float]:
        try:
            return self._sensors.all_temperatures()
        except OSError:
            return {}

    def _fans(self) -> dict[str, float]:
        try:
            return self._sensors.fan_speeds()
        except OSError:
            return {}

    @staticmethod
    def _safe(reader: Callable[[], _T | None]) -> _T | None:
        try:
            return reader()
        except (OSError, ValueError):
            return None
