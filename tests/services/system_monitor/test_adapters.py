from __future__ import annotations

import types
from pathlib import Path

import pytest

from sysbar.services.system_monitor import adapters
from sysbar.services.system_monitor.adapters import (
    DiskUsageReader,
    GpuReaderChain,
    ProcfsReader,
    PsutilSensorReader,
    SysfsPowerReader,
    _amd_busy_path,
    _amd_temp_path,
    _nvml_temperature,
    _nvml_utilization,
    _nvml_value,
    _read_sysfs_float,
)


class FakeSensorEntry:
    def __init__(self, current: float, label: str = "") -> None:
        self.current = current
        self.label = label


class FakePsutil:
    """Stand-in for the ``psutil`` module used by PsutilSensorReader."""

    def __init__(
        self,
        temps: dict[str, list[FakeSensorEntry]] | None = None,
        fans: dict[str, list[FakeSensorEntry]] | None = None,
    ) -> None:
        self._temps = temps
        self._fans = fans

    def sensors_temperatures(self) -> dict[str, list[FakeSensorEntry]]:
        return self._temps or {}

    def sensors_fans(self) -> dict[str, list[FakeSensorEntry]]:
        return self._fans or {}


def _install_psutil(monkeypatch: pytest.MonkeyPatch, fake: FakePsutil) -> None:
    monkeypatch.setitem(__import__("sys").modules, "psutil", fake)


# --------------------------------------------------------------------------- #
# _read_sysfs_float
# --------------------------------------------------------------------------- #


def test_read_sysfs_float_none_path_returns_none() -> None:
    assert _read_sysfs_float(None) is None


def test_read_sysfs_float_parses_value(tmp_path: Path) -> None:
    target = tmp_path / "value"
    target.write_text("  42.5\n")
    assert _read_sysfs_float(target) == 42.5


def test_read_sysfs_float_unparseable_returns_none(tmp_path: Path) -> None:
    target = tmp_path / "value"
    target.write_text("not-a-number")
    assert _read_sysfs_float(target) is None


def test_read_sysfs_float_missing_file_returns_none(tmp_path: Path) -> None:
    assert _read_sysfs_float(tmp_path / "absent") is None


# --------------------------------------------------------------------------- #
# SysfsPowerReader.on_battery
# --------------------------------------------------------------------------- #


def test_on_battery_true_when_ac_offline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ac = tmp_path / "AC0"
    ac.mkdir()
    (ac / "online").write_text("0\n")
    monkeypatch.setattr(adapters, "POWER_SUPPLY_PATH", tmp_path)
    assert SysfsPowerReader().on_battery() is True


def test_on_battery_false_when_ac_online(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ac = tmp_path / "ADP1"
    ac.mkdir()
    (ac / "online").write_text("1\n")
    monkeypatch.setattr(adapters, "POWER_SUPPLY_PATH", tmp_path)
    assert SysfsPowerReader().on_battery() is False


def test_on_battery_none_when_no_ac_adapter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(adapters, "POWER_SUPPLY_PATH", tmp_path)
    assert SysfsPowerReader().on_battery() is None


# --------------------------------------------------------------------------- #
# SysfsPowerReader.charging
# --------------------------------------------------------------------------- #


def test_charging_true_when_status_charging(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bat = tmp_path / "BAT0"
    bat.mkdir()
    (bat / "status").write_text("Charging\n")
    monkeypatch.setattr(adapters, "POWER_SUPPLY_PATH", tmp_path)
    assert SysfsPowerReader().charging() is True


def test_charging_false_when_status_discharging(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bat = tmp_path / "BAT0"
    bat.mkdir()
    (bat / "status").write_text("Discharging\n")
    monkeypatch.setattr(adapters, "POWER_SUPPLY_PATH", tmp_path)
    assert SysfsPowerReader().charging() is False


def test_charging_none_when_no_battery(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(adapters, "POWER_SUPPLY_PATH", tmp_path)
    assert SysfsPowerReader().charging() is None


def test_charging_none_when_status_file_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "BAT0").mkdir()
    monkeypatch.setattr(adapters, "POWER_SUPPLY_PATH", tmp_path)
    assert SysfsPowerReader().charging() is None


# --------------------------------------------------------------------------- #
# SysfsPowerReader.power_watts / battery_percent
# --------------------------------------------------------------------------- #


def test_power_watts_converts_microwatts_to_watts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bat = tmp_path / "BAT0"
    bat.mkdir()
    (bat / "power_now").write_text("12500000\n")
    monkeypatch.setattr(adapters, "POWER_SUPPLY_PATH", tmp_path)
    assert SysfsPowerReader().power_watts() == 12.5


def test_power_watts_none_when_no_battery(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(adapters, "POWER_SUPPLY_PATH", tmp_path)
    assert SysfsPowerReader().power_watts() is None


def test_battery_percent_reads_capacity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bat = tmp_path / "BAT0"
    bat.mkdir()
    (bat / "capacity").write_text("87\n")
    monkeypatch.setattr(adapters, "POWER_SUPPLY_PATH", tmp_path)
    assert SysfsPowerReader().battery_percent() == 87.0


# --------------------------------------------------------------------------- #
# GpuReaderChain.utilization
# --------------------------------------------------------------------------- #


def test_utilization_prefers_nvml_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapters, "_nvml_value", lambda _reader: 73.0)
    assert GpuReaderChain().utilization() == 73.0


def test_utilization_falls_back_to_amd_sysfs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    busy = tmp_path / "gpu_busy_percent"
    busy.write_text("40\n")
    monkeypatch.setattr(adapters, "_nvml_value", lambda _reader: None)
    monkeypatch.setattr(adapters, "_amd_busy_path", lambda: busy)
    assert GpuReaderChain().utilization() == 40.0


def test_utilization_none_when_no_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapters, "_nvml_value", lambda _reader: None)
    monkeypatch.setattr(adapters, "_amd_busy_path", lambda: None)
    assert GpuReaderChain().utilization() is None


# --------------------------------------------------------------------------- #
# GpuReaderChain.temperature
# --------------------------------------------------------------------------- #


def test_temperature_prefers_nvml_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapters, "_nvml_value", lambda _reader: 65.0)
    assert GpuReaderChain().temperature() == 65.0


def test_temperature_converts_amd_millidegrees(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    temp = tmp_path / "temp1_input"
    temp.write_text("55000\n")
    monkeypatch.setattr(adapters, "_nvml_value", lambda _reader: None)
    monkeypatch.setattr(adapters, "_amd_temp_path", lambda: temp)
    assert GpuReaderChain().temperature() == 55.0


def test_temperature_none_when_no_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapters, "_nvml_value", lambda _reader: None)
    monkeypatch.setattr(adapters, "_amd_temp_path", lambda: None)
    assert GpuReaderChain().temperature() is None


# --------------------------------------------------------------------------- #
# PsutilSensorReader.cpu_temperature
# --------------------------------------------------------------------------- #


def test_cpu_temperature_returns_first_present_chip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakePsutil(
        temps={
            "acpitz": [FakeSensorEntry(current=40.0)],
            "coretemp": [FakeSensorEntry(current=58.0)],
        }
    )
    _install_psutil(monkeypatch, fake)
    # coretemp is earlier in the priority tuple than acpitz.
    assert PsutilSensorReader().cpu_temperature() == 58.0


def test_cpu_temperature_none_when_no_known_chip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakePsutil(temps={"unknown": [FakeSensorEntry(current=99.0)]})
    _install_psutil(monkeypatch, fake)
    assert PsutilSensorReader().cpu_temperature() is None


# --------------------------------------------------------------------------- #
# PsutilSensorReader.all_temperatures
# --------------------------------------------------------------------------- #


def test_all_temperatures_keys_use_chip_and_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakePsutil(temps={"coretemp": [FakeSensorEntry(current=58.0, label="Core 0")]})
    _install_psutil(monkeypatch, fake)
    assert PsutilSensorReader().all_temperatures() == {"coretemp/Core 0": 58.0}


def test_all_temperatures_falls_back_to_chip_when_no_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakePsutil(temps={"k10temp": [FakeSensorEntry(current=45.0, label="")]})
    _install_psutil(monkeypatch, fake)
    assert PsutilSensorReader().all_temperatures() == {"k10temp/k10temp": 45.0}


# --------------------------------------------------------------------------- #
# PsutilSensorReader.fan_speeds
# --------------------------------------------------------------------------- #


def test_fan_speeds_keys_use_chip_and_label_as_float(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakePsutil(fans={"dell_smm": [FakeSensorEntry(current=1200, label="fan1")]})
    _install_psutil(monkeypatch, fake)
    assert PsutilSensorReader().fan_speeds() == {"dell_smm/fan1": 1200.0}


def test_fan_speeds_falls_back_to_chip_when_no_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakePsutil(fans={"thinkpad": [FakeSensorEntry(current=3000, label="")]})
    _install_psutil(monkeypatch, fake)
    assert PsutilSensorReader().fan_speeds() == {"thinkpad/thinkpad": 3000.0}


# --------------------------------------------------------------------------- #
# PsutilSensorReader — module without the sensors_* attributes
# --------------------------------------------------------------------------- #


class FakePsutilNoSensors:
    """Stand-in psutil missing sensors_temperatures / sensors_fans entirely."""


def test_cpu_temperature_none_when_psutil_lacks_sensors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_psutil(monkeypatch, FakePsutilNoSensors())  # type: ignore[arg-type]
    assert PsutilSensorReader().cpu_temperature() is None


def test_all_temperatures_empty_when_psutil_lacks_sensors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_psutil(monkeypatch, FakePsutilNoSensors())  # type: ignore[arg-type]
    assert PsutilSensorReader().all_temperatures() == {}


def test_fan_speeds_empty_when_psutil_lacks_sensors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_psutil(monkeypatch, FakePsutilNoSensors())  # type: ignore[arg-type]
    assert PsutilSensorReader().fan_speeds() == {}


# --------------------------------------------------------------------------- #
# SysfsPowerReader.on_battery — AC dir present but online unreadable
# --------------------------------------------------------------------------- #


def test_on_battery_none_when_online_unreadable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # AC directory exists but the ``online`` file is absent, so the loop reads
    # None and falls through to the final ``return None``.
    (tmp_path / "AC0").mkdir()
    monkeypatch.setattr(adapters, "POWER_SUPPLY_PATH", tmp_path)
    assert SysfsPowerReader().on_battery() is None


# --------------------------------------------------------------------------- #
# ProcfsReader.read_psi_memory
# --------------------------------------------------------------------------- #


def test_read_psi_memory_returns_text(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    psi = tmp_path / "memory"
    psi.write_text("some avg10=0.00\n")
    monkeypatch.setattr(adapters, "PROC_PRESSURE_MEMORY", psi)
    assert ProcfsReader().read_psi_memory() == "some avg10=0.00\n"


def test_read_psi_memory_none_on_oserror(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(adapters, "PROC_PRESSURE_MEMORY", tmp_path / "absent")
    assert ProcfsReader().read_psi_memory() is None


# --------------------------------------------------------------------------- #
# _amd_busy_path / _amd_temp_path
# --------------------------------------------------------------------------- #


def test_amd_busy_path_returns_existing_candidate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    device = tmp_path / "card0" / "device"
    device.mkdir(parents=True)
    busy = device / "gpu_busy_percent"
    busy.write_text("12\n")
    monkeypatch.setattr(adapters, "DRM_PATH", tmp_path)
    assert _amd_busy_path() == busy


def test_amd_busy_path_none_when_no_match(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "card0" / "device").mkdir(parents=True)
    monkeypatch.setattr(adapters, "DRM_PATH", tmp_path)
    assert _amd_busy_path() is None


def test_amd_temp_path_returns_existing_candidate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    hwmon = tmp_path / "card0" / "device" / "hwmon" / "hwmon0"
    hwmon.mkdir(parents=True)
    temp = hwmon / "temp1_input"
    temp.write_text("50000\n")
    monkeypatch.setattr(adapters, "DRM_PATH", tmp_path)
    assert _amd_temp_path() == temp


def test_amd_temp_path_none_when_no_hwmon_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "card0" / "device" / "hwmon").mkdir(parents=True)
    monkeypatch.setattr(adapters, "DRM_PATH", tmp_path)
    assert _amd_temp_path() is None


def test_amd_temp_path_skips_hwmon_without_temp_input(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A hwmon directory exists but lacks ``temp1_input``, so the inner loop
    # continues past it and the function returns None.
    (tmp_path / "card0" / "device" / "hwmon" / "hwmon0").mkdir(parents=True)
    monkeypatch.setattr(adapters, "DRM_PATH", tmp_path)
    assert _amd_temp_path() is None


# --------------------------------------------------------------------------- #
# _nvml_value / _nvml_utilization / _nvml_temperature
# --------------------------------------------------------------------------- #


class FakeUtilization:
    def __init__(self, gpu: float) -> None:
        self.gpu = gpu


def _fake_pynvml(events: list[str]) -> types.SimpleNamespace:
    """Build a ``pynvml`` stand-in. The CamelCase names mirror the real API the
    code calls, so they are set as namespace attributes rather than methods."""
    return types.SimpleNamespace(
        NVML_TEMPERATURE_GPU=0,
        nvmlInit=lambda: events.append("init"),
        nvmlShutdown=lambda: events.append("shutdown"),
        nvmlDeviceGetHandleByIndex=lambda _index: "handle",
        nvmlDeviceGetUtilizationRates=lambda _handle: FakeUtilization(gpu=77),
        nvmlDeviceGetTemperature=lambda _handle, _sensor: 61,
    )


def _install_pynvml(monkeypatch: pytest.MonkeyPatch, fake: object) -> None:
    monkeypatch.setitem(__import__("sys").modules, "pynvml", fake)


def test_nvml_value_returns_reader_result_and_shuts_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    _install_pynvml(monkeypatch, _fake_pynvml(events))
    result = _nvml_value(lambda pynvml, handle: 42.0)
    assert result == 42.0
    assert events == ["init", "shutdown"]


def test_nvml_value_none_when_init_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise() -> None:
        raise RuntimeError("no driver")

    fake = types.SimpleNamespace(nvmlInit=_raise)
    _install_pynvml(monkeypatch, fake)
    assert _nvml_value(lambda pynvml, handle: 1.0) is None


def test_nvml_utilization_extracts_gpu_as_float(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_pynvml(monkeypatch, _fake_pynvml([]))
    assert _nvml_value(_nvml_utilization) == 77.0


def test_nvml_temperature_extracts_value_as_float(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_pynvml(monkeypatch, _fake_pynvml([]))
    assert _nvml_value(_nvml_temperature) == 61.0


# --------------------------------------------------------------------------- #
# DiskUsageReader.usage_percent
# --------------------------------------------------------------------------- #


def _usage(total: int, used: int) -> types.SimpleNamespace:
    """Stand-in for ``shutil.disk_usage`` result (total/used/free fields)."""
    return types.SimpleNamespace(total=total, used=used, free=total - used)


def test_usage_percent_computes_used_over_total() -> None:
    reader = DiskUsageReader(usage=lambda _path: _usage(total=200, used=50))
    assert reader.usage_percent() == 25.0


def test_usage_percent_full_disk_returns_hundred() -> None:
    reader = DiskUsageReader(usage=lambda _path: _usage(total=100, used=100))
    assert reader.usage_percent() == 100.0


def test_usage_percent_none_when_total_zero() -> None:
    reader = DiskUsageReader(usage=lambda _path: _usage(total=0, used=0))
    assert reader.usage_percent() is None


def test_usage_percent_none_when_usage_raises() -> None:
    def _raise(_path: str) -> types.SimpleNamespace:
        raise OSError("path unreadable")

    assert DiskUsageReader(usage=_raise).usage_percent() is None
