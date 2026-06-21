from __future__ import annotations

from datetime import datetime, timedelta

from sysbar.services.system_monitor.alerting import (
    ALERT_BATTERY,
    ALERT_CPU,
    ALERT_DISK,
    ALERT_MEMORY,
    ALERT_TEMPERATURE,
    AlertEngine,
    AlertThresholds,
)
from sysbar.services.system_monitor.snapshot import SystemSnapshot


class FakeClock:
    """Manually advanced clock for the CPU sustained-breach window."""

    def __init__(self) -> None:
        self._now = datetime(2024, 1, 1, 12, 0, 0)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


def _engine(thresholds: AlertThresholds, clock: FakeClock | None = None) -> AlertEngine:
    return AlertEngine(thresholds=lambda: thresholds, clock=(clock or FakeClock()).now)


# --------------------------------------------------------------------------- #
# CPU — sustained breach
# --------------------------------------------------------------------------- #


def test_cpu_below_threshold_does_not_alert() -> None:
    engine = _engine(AlertThresholds(cpu_percent=90, cpu_seconds=10))
    assert engine.evaluate(SystemSnapshot(cpu_percent=50.0)) == []


def test_cpu_above_threshold_but_not_long_enough_does_not_alert() -> None:
    clock = FakeClock()
    engine = _engine(AlertThresholds(cpu_percent=90, cpu_seconds=10), clock)
    assert engine.evaluate(SystemSnapshot(cpu_percent=95.0)) == []
    clock.advance(5)
    assert engine.evaluate(SystemSnapshot(cpu_percent=95.0)) == []


def test_cpu_sustained_breach_fires_once() -> None:
    clock = FakeClock()
    engine = _engine(AlertThresholds(cpu_percent=90, cpu_seconds=10), clock)
    engine.evaluate(SystemSnapshot(cpu_percent=95.0))
    clock.advance(10)
    fired = engine.evaluate(SystemSnapshot(cpu_percent=96.0))
    assert [a.key for a in fired] == [ALERT_CPU]
    clock.advance(5)
    assert engine.evaluate(SystemSnapshot(cpu_percent=97.0)) == []


def test_cpu_rearms_after_recovery() -> None:
    clock = FakeClock()
    engine = _engine(AlertThresholds(cpu_percent=90, cpu_seconds=10), clock)
    engine.evaluate(SystemSnapshot(cpu_percent=95.0))
    clock.advance(10)
    assert engine.evaluate(SystemSnapshot(cpu_percent=95.0))  # fires
    engine.evaluate(SystemSnapshot(cpu_percent=20.0))  # recovers, resets
    clock.advance(10)
    refired = engine.evaluate(SystemSnapshot(cpu_percent=99.0))
    clock.advance(10)
    refired = engine.evaluate(SystemSnapshot(cpu_percent=99.0))
    assert [a.key for a in refired] == [ALERT_CPU]


# --------------------------------------------------------------------------- #
# Memory / disk — instantaneous ceiling with hysteresis
# --------------------------------------------------------------------------- #


def test_memory_above_threshold_fires_once_then_rearms() -> None:
    engine = _engine(AlertThresholds(memory_percent=90))
    assert [a.key for a in engine.evaluate(SystemSnapshot(memory_percent=92.0))] == [ALERT_MEMORY]
    assert engine.evaluate(SystemSnapshot(memory_percent=93.0)) == []  # no spam
    engine.evaluate(SystemSnapshot(memory_percent=10.0))  # recover
    assert [a.key for a in engine.evaluate(SystemSnapshot(memory_percent=95.0))] == [ALERT_MEMORY]


def test_disk_full_fires() -> None:
    engine = _engine(AlertThresholds(disk_percent=85))
    fired = engine.evaluate(SystemSnapshot(disk_percent=88.0))
    assert [a.key for a in fired] == [ALERT_DISK]
    assert "88%" in fired[0].body


# --------------------------------------------------------------------------- #
# Temperature — cpu_temp preferred, hottest sensor as fallback
# --------------------------------------------------------------------------- #


def test_temperature_uses_cpu_temp_when_present() -> None:
    engine = _engine(AlertThresholds(temperature_celsius=80))
    fired = engine.evaluate(SystemSnapshot(cpu_temp_celsius=85.0))
    assert [a.key for a in fired] == [ALERT_TEMPERATURE]


def test_temperature_falls_back_to_hottest_sensor() -> None:
    engine = _engine(AlertThresholds(temperature_celsius=80))
    snap = SystemSnapshot(cpu_temp_celsius=None, temperatures={"gpu": 70.0, "vrm": 88.0})
    assert [a.key for a in engine.evaluate(snap)] == [ALERT_TEMPERATURE]


def test_temperature_no_alert_when_no_sensor() -> None:
    engine = _engine(AlertThresholds(temperature_celsius=80))
    assert engine.evaluate(SystemSnapshot(cpu_temp_celsius=None, temperatures={})) == []


# --------------------------------------------------------------------------- #
# Battery — only on battery and at/under threshold
# --------------------------------------------------------------------------- #


def test_battery_low_on_battery_fires() -> None:
    engine = _engine(AlertThresholds(battery_percent=15))
    fired = engine.evaluate(SystemSnapshot(battery_percent=12.0, on_battery=True))
    assert [a.key for a in fired] == [ALERT_BATTERY]


def test_battery_low_while_charging_does_not_fire() -> None:
    engine = _engine(AlertThresholds(battery_percent=15))
    assert engine.evaluate(SystemSnapshot(battery_percent=12.0, on_battery=False)) == []


def test_battery_above_threshold_does_not_fire() -> None:
    engine = _engine(AlertThresholds(battery_percent=15))
    assert engine.evaluate(SystemSnapshot(battery_percent=40.0, on_battery=True)) == []


def test_battery_sustained_low_fires_only_on_the_rising_edge() -> None:
    engine = _engine(AlertThresholds(battery_percent=15))
    first = engine.evaluate(SystemSnapshot(battery_percent=12.0, on_battery=True))
    second = engine.evaluate(SystemSnapshot(battery_percent=11.0, on_battery=True))
    assert [a.key for a in first] == [ALERT_BATTERY]
    assert second == []


def test_battery_rearms_after_recovering_above_threshold() -> None:
    engine = _engine(AlertThresholds(battery_percent=15))
    engine.evaluate(SystemSnapshot(battery_percent=12.0, on_battery=True))
    engine.evaluate(SystemSnapshot(battery_percent=40.0, on_battery=True))
    refired = engine.evaluate(SystemSnapshot(battery_percent=10.0, on_battery=True))
    assert [a.key for a in refired] == [ALERT_BATTERY]


# --------------------------------------------------------------------------- #
# Disabled thresholds and missing data
# --------------------------------------------------------------------------- #


def test_zero_threshold_disables_alert() -> None:
    engine = _engine(AlertThresholds(cpu_percent=0, memory_percent=0))
    assert engine.evaluate(SystemSnapshot(cpu_percent=100.0, memory_percent=100.0)) == []


def test_missing_metric_does_not_alert() -> None:
    engine = _engine(AlertThresholds(memory_percent=90, disk_percent=90))
    assert engine.evaluate(SystemSnapshot(memory_percent=None, disk_percent=None)) == []


def test_multiple_alerts_fire_together() -> None:
    engine = _engine(AlertThresholds(memory_percent=90, disk_percent=90))
    fired = {a.key for a in engine.evaluate(SystemSnapshot(memory_percent=95.0, disk_percent=95.0))}
    assert fired == {ALERT_MEMORY, ALERT_DISK}
