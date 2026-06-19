"""Concrete source adapters (the system boundary).

Each adapter implements a port from :mod:`ports` by reading procfs/sysfs,
``psutil``, NVML or UPower. They stay thin (delegating computation to the pure
parsers) and degrade to ``None``/empty when a source is missing. Mocked in tests.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ...core.constants import (
    DRM_PATH,
    POWER_SUPPLY_PATH,
    PROC_MEMINFO,
    PROC_NET_DEV,
    PROC_PRESSURE_MEMORY,
    PROC_STAT,
    PROC_UPTIME,
)

log = logging.getLogger(__name__)

_CPU_TEMP_CHIPS = ("coretemp", "k10temp", "zenpower", "acpitz")


class ProcfsReader:
    """Reads raw procfs files."""

    def read_stat(self) -> str:
        return PROC_STAT.read_text()  # pragma: no cover - passthrough procfs read_text

    def read_meminfo(self) -> str:
        return PROC_MEMINFO.read_text()  # pragma: no cover - passthrough procfs read_text

    def read_uptime(self) -> str:
        return PROC_UPTIME.read_text()  # pragma: no cover - passthrough procfs read_text

    def read_net_dev(self) -> str:
        return PROC_NET_DEV.read_text()  # pragma: no cover - passthrough procfs read_text

    def read_psi_memory(self) -> str | None:
        try:
            return PROC_PRESSURE_MEMORY.read_text()
        except OSError:
            return None


class PsutilSensorReader:
    """Reads temperatures via ``psutil.sensors_temperatures``."""

    def cpu_temperature(self) -> float | None:
        import psutil

        if not hasattr(psutil, "sensors_temperatures"):
            return None
        temps = psutil.sensors_temperatures()
        for chip in _CPU_TEMP_CHIPS:
            if temps.get(chip):
                return temps[chip][0].current
        return None

    def all_temperatures(self) -> dict[str, float]:
        import psutil

        if not hasattr(psutil, "sensors_temperatures"):
            return {}
        result: dict[str, float] = {}
        for chip, entries in psutil.sensors_temperatures().items():
            for entry in entries:
                label = entry.label or chip
                result[f"{chip}/{label}"] = entry.current
        return result

    def fan_speeds(self) -> dict[str, float]:
        import psutil

        if not hasattr(psutil, "sensors_fans"):
            return {}
        result: dict[str, float] = {}
        for chip, entries in psutil.sensors_fans().items():
            for entry in entries:
                label = entry.label or chip
                result[f"{chip}/{label}"] = float(entry.current)
        return result


class GpuReaderChain:
    """NVIDIA via NVML, falling back to AMD sysfs; ``None`` when no GPU."""

    def utilization(self) -> float | None:
        nvidia = _nvml_value(_nvml_utilization)
        return nvidia if nvidia is not None else _read_sysfs_float(_amd_busy_path())

    def temperature(self) -> float | None:
        nvidia = _nvml_value(_nvml_temperature)
        if nvidia is not None:
            return nvidia
        millidegrees = _read_sysfs_float(_amd_temp_path())
        return millidegrees / 1000.0 if millidegrees is not None else None


class SysfsPowerReader:
    """Reads battery/power from ``/sys/class/power_supply``."""

    def battery_percent(self) -> float | None:
        return _read_sysfs_float(_battery_path("capacity"))

    def on_battery(self) -> bool | None:
        for ac in POWER_SUPPLY_PATH.glob("A[CD]*"):
            online = _read_sysfs_float(ac / "online")
            if online is not None:
                return online < 1.0
        return None

    def charging(self) -> bool | None:
        path = _battery_path("status")
        if path is None or not path.exists():
            return None
        return path.read_text().strip() == "Charging"

    def power_watts(self) -> float | None:
        microwatts = _read_sysfs_float(_battery_path("power_now"))
        return microwatts / 1_000_000.0 if microwatts is not None else None


def _battery_path(leaf: str) -> Path | None:
    for battery in sorted(POWER_SUPPLY_PATH.glob("BAT*")):
        return battery / leaf
    return None


def _amd_busy_path() -> Path | None:
    for card in sorted(DRM_PATH.glob("card[0-9]")):
        candidate = card / "device" / "gpu_busy_percent"
        if candidate.exists():
            return candidate
    return None


def _amd_temp_path() -> Path | None:
    for card in sorted(DRM_PATH.glob("card[0-9]")):
        for hwmon in (card / "device" / "hwmon").glob("hwmon*"):
            candidate = hwmon / "temp1_input"
            if candidate.exists():
                return candidate
    return None


def _read_sysfs_float(path: Path | None) -> float | None:
    if path is None:
        return None
    try:
        return float(path.read_text().strip())
    except (OSError, ValueError):
        return None


def _nvml_value(reader: Callable[[Any, Any], float]) -> float | None:
    try:
        import pynvml

        pynvml.nvmlInit()
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            return reader(pynvml, handle)
        finally:
            pynvml.nvmlShutdown()
    except Exception:
        return None


def _nvml_utilization(pynvml: Any, handle: Any) -> float:
    return float(pynvml.nvmlDeviceGetUtilizationRates(handle).gpu)


def _nvml_temperature(pynvml: Any, handle: Any) -> float:
    return float(pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU))
