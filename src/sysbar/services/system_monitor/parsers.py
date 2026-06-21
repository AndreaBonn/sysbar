"""Pure parsers for procfs sources.

Each function turns raw ``/proc`` text into typed values. They contain no I/O,
so they are unit-tested with concrete fixtures (the heart of the monitor tests).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from ...core.constants import (
    MEMORY_PRESSURE_CRITICAL,
    MEMORY_PRESSURE_WARNING,
    UPOWER_STATE_CHARGING,
)
from .models import PeripheralBattery

_UPOWER_KEY_TYPE = "Type"
_UPOWER_KEY_MODEL = "Model"
_UPOWER_KEY_PERCENTAGE = "Percentage"
_UPOWER_KEY_STATE = "State"
_UPOWER_KEY_POWER_SUPPLY = "PowerSupply"
_UPOWER_KEY_IS_PRESENT = "IsPresent"


@dataclass(frozen=True)
class CpuSample:
    """Cumulative CPU jiffies for one logical CPU (or the aggregate)."""

    total: int
    idle: int


@dataclass(frozen=True)
class MemInfo:
    """Selected fields from ``/proc/meminfo`` (kibibytes)."""

    total_kb: int
    available_kb: int


def parse_cpu_stat(text: str) -> dict[str, CpuSample]:
    """Parse ``/proc/stat`` CPU lines into samples keyed by ``cpu``/``cpuN``.

    ``idle`` aggregates the idle and iowait jiffies; ``total`` is the sum of all
    reported counters.
    """
    samples: dict[str, CpuSample] = {}
    for line in text.splitlines():
        if not line.startswith("cpu"):
            continue
        fields = line.split()
        name = fields[0]
        values = [int(value) for value in fields[1:]]
        if len(values) < 5:
            continue
        idle = values[3] + values[4]
        samples[name] = CpuSample(total=sum(values), idle=idle)
    return samples


def cpu_busy_percent(previous: CpuSample, current: CpuSample) -> float:
    """Busy CPU percentage between two cumulative samples (0..100)."""
    delta_total = current.total - previous.total
    delta_idle = current.idle - previous.idle
    if delta_total <= 0:
        return 0.0
    busy = delta_total - delta_idle
    return max(0.0, min(100.0, 100.0 * busy / delta_total))


def parse_meminfo(text: str) -> MemInfo:
    """Parse ``MemTotal`` and ``MemAvailable`` from ``/proc/meminfo``."""
    fields: dict[str, int] = {}
    for line in text.splitlines():
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts and parts[0].isdigit():
            fields[key.strip()] = int(parts[0])
    return MemInfo(total_kb=fields.get("MemTotal", 0), available_kb=fields.get("MemAvailable", 0))


def memory_used_percent(info: MemInfo) -> float:
    """Used memory as a percentage of total (0..100)."""
    if info.total_kb <= 0:
        return 0.0
    used = info.total_kb - info.available_kb
    return max(0.0, min(100.0, 100.0 * used / info.total_kb))


def parse_uptime(text: str) -> float:
    """Parse the uptime in seconds from ``/proc/uptime``."""
    return float(text.split()[0])


def parse_net_dev(text: str) -> dict[str, tuple[int, int]]:
    """Parse ``/proc/net/dev`` into ``iface -> (rx_bytes, tx_bytes)``."""
    counters: dict[str, tuple[int, int]] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        name, _, rest = line.partition(":")
        values = rest.split()
        if len(values) < 9:
            continue
        counters[name.strip()] = (int(values[0]), int(values[8]))
    return counters


def rate_per_second(previous_bytes: int, current_bytes: int, interval_seconds: float) -> float:
    """Throughput in bytes/second between two cumulative byte counters."""
    if interval_seconds <= 0:
        return 0.0
    return max(0.0, (current_bytes - previous_bytes) / interval_seconds)


def parse_psi_some_avg10(text: str) -> float | None:
    """Parse ``some avg10`` from ``/proc/pressure/memory`` (None if absent)."""
    for line in text.splitlines():
        if not line.startswith("some"):
            continue
        for token in line.split():
            if token.startswith("avg10="):
                return float(token.split("=", 1)[1])
    return None


def memory_pressure_level(avg10: float) -> str:
    """Map a PSI ``some avg10`` value to a named pressure level."""
    if avg10 >= MEMORY_PRESSURE_CRITICAL:
        return "critical"
    if avg10 >= MEMORY_PRESSURE_WARNING:
        return "warning"
    return "normal"


def parse_upower_devices(
    devices: Iterable[dict[str, Any]],
) -> tuple[PeripheralBattery, ...]:
    """Turn raw UPower device-property dicts into peripheral battery readings.

    Keeps only connected peripherals that report a charge: entries flagged as a
    power supply (the laptop battery and AC line) are dropped, as are absent
    devices and those at 0% (no real reading). Input order is preserved.

    Parameters
    ----------
    devices
        One mapping of ``org.freedesktop.UPower.Device`` properties per device,
        as returned by ``GetAll`` (already unpacked to native Python values).
    """
    result: list[PeripheralBattery] = []
    for props in devices:
        if bool(props.get(_UPOWER_KEY_POWER_SUPPLY, False)):
            continue
        if not bool(props.get(_UPOWER_KEY_IS_PRESENT, True)):
            continue
        percent = float(props.get(_UPOWER_KEY_PERCENTAGE, 0.0))
        if percent <= 0.0:
            continue
        result.append(
            PeripheralBattery(
                model=str(props.get(_UPOWER_KEY_MODEL, "")).strip(),
                kind=int(props.get(_UPOWER_KEY_TYPE, 0)),
                percent=percent,
                charging=int(props.get(_UPOWER_KEY_STATE, 0)) == UPOWER_STATE_CHARGING,
            )
        )
    return tuple(result)
