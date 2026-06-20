"""Threshold alerting over system snapshots (port of a watchdog).

The engine is pure with respect to its injected clock and threshold provider:
given a sequence of :class:`SystemSnapshot` it returns the alerts that fire on
this tick, and nothing else. Each metric fires once on the rising edge (when it
crosses its threshold) and rearms only after the value falls back, so a sustained
breach does not spam notifications. CPU additionally requires the breach to hold
for a configured duration, which is why a clock is injected.

Wiring (timer, notifier) lives in the application; this module never imports GI.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from ...core.i18n import _
from .snapshot import SystemSnapshot

_DISABLED = 0

ALERT_CPU = "cpu"
ALERT_MEMORY = "memory"
ALERT_DISK = "disk"
ALERT_TEMPERATURE = "temperature"
ALERT_BATTERY = "battery"


@dataclass(frozen=True)
class AlertThresholds:
    """User-configured alert limits; ``0`` disables an individual alert."""

    cpu_percent: int = _DISABLED
    cpu_seconds: int = _DISABLED
    memory_percent: int = _DISABLED
    disk_percent: int = _DISABLED
    temperature_celsius: int = _DISABLED
    battery_percent: int = _DISABLED


@dataclass(frozen=True)
class Alert:
    """A fired alert, ready to be turned into a desktop notification."""

    key: str
    title: str
    body: str


class AlertEngine:
    """Turns snapshots into edge-triggered alerts using configured thresholds."""

    def __init__(
        self,
        thresholds: Callable[[], AlertThresholds],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._thresholds = thresholds
        self._clock = clock or datetime.now
        self._active: set[str] = set()
        self._cpu_breach_since: datetime | None = None

    def evaluate(self, snapshot: SystemSnapshot) -> list[Alert]:
        """Return the alerts that fire on this snapshot (rising edge only)."""
        limits = self._thresholds()
        alerts: list[Alert] = []
        self._eval_cpu(snapshot, limits, alerts)
        self._eval_memory(snapshot, limits, alerts)
        self._eval_disk(snapshot, limits, alerts)
        self._eval_temperature(snapshot, limits, alerts)
        self._eval_battery(snapshot, limits, alerts)
        return alerts

    def _eval_cpu(
        self, snapshot: SystemSnapshot, limits: AlertThresholds, alerts: list[Alert]
    ) -> None:
        value = snapshot.cpu_percent
        if limits.cpu_percent <= _DISABLED or value is None or value < limits.cpu_percent:
            self._cpu_breach_since = None
            self._active.discard(ALERT_CPU)
            return
        now = self._clock()
        if self._cpu_breach_since is None:
            self._cpu_breach_since = now
        held = (now - self._cpu_breach_since).total_seconds()
        if held >= limits.cpu_seconds and self._fire(ALERT_CPU):
            alerts.append(
                Alert(
                    key=ALERT_CPU,
                    title=_("High CPU usage"),
                    body=_(
                        "CPU has stayed above {threshold}% for {seconds}s (now {value}%)."
                    ).format(
                        threshold=limits.cpu_percent,
                        seconds=limits.cpu_seconds,
                        value=round(value),
                    ),
                )
            )

    def _eval_memory(
        self, snapshot: SystemSnapshot, limits: AlertThresholds, alerts: list[Alert]
    ) -> None:
        self._eval_ceiling(
            value=snapshot.memory_percent,
            threshold=limits.memory_percent,
            key=ALERT_MEMORY,
            title=_("High memory usage"),
            body_template=_("Memory usage is {value}% (threshold {threshold}%)."),
            alerts=alerts,
        )

    def _eval_disk(
        self, snapshot: SystemSnapshot, limits: AlertThresholds, alerts: list[Alert]
    ) -> None:
        self._eval_ceiling(
            value=snapshot.disk_percent,
            threshold=limits.disk_percent,
            key=ALERT_DISK,
            title=_("Low disk space"),
            body_template=_("Root filesystem is {value}% full (threshold {threshold}%)."),
            alerts=alerts,
        )

    def _eval_temperature(
        self, snapshot: SystemSnapshot, limits: AlertThresholds, alerts: list[Alert]
    ) -> None:
        self._eval_ceiling(
            value=_hottest(snapshot),
            threshold=limits.temperature_celsius,
            key=ALERT_TEMPERATURE,
            title=_("High temperature"),
            body_template=_("Temperature is {value}°C (threshold {threshold}°C)."),
            alerts=alerts,
        )

    def _eval_battery(
        self, snapshot: SystemSnapshot, limits: AlertThresholds, alerts: list[Alert]
    ) -> None:
        value = snapshot.battery_percent
        if (
            limits.battery_percent <= _DISABLED
            or value is None
            or not snapshot.on_battery
            or value > limits.battery_percent
        ):
            self._active.discard(ALERT_BATTERY)
            return
        if self._fire(ALERT_BATTERY):
            alerts.append(
                Alert(
                    key=ALERT_BATTERY,
                    title=_("Low battery"),
                    body=_("Battery is at {value}% (threshold {threshold}%).").format(
                        value=round(value), threshold=limits.battery_percent
                    ),
                )
            )

    def _eval_ceiling(
        self,
        *,
        value: float | None,
        threshold: int,
        key: str,
        title: str,
        body_template: str,
        alerts: list[Alert],
    ) -> None:
        """Fire ``key`` when ``value`` rises to ``threshold``; rearm when it falls."""
        if threshold <= _DISABLED or value is None or value < threshold:
            self._active.discard(key)
            return
        if self._fire(key):
            alerts.append(
                Alert(
                    key=key,
                    title=title,
                    body=body_template.format(value=round(value), threshold=threshold),
                )
            )

    def _fire(self, key: str) -> bool:
        """Mark ``key`` active; return ``True`` only on the rising edge."""
        if key in self._active:
            return False
        self._active.add(key)
        return True


def _hottest(snapshot: SystemSnapshot) -> float | None:
    """The CPU temperature, or the hottest reported sensor as a fallback."""
    if snapshot.cpu_temp_celsius is not None:
        return snapshot.cpu_temp_celsius
    return max(snapshot.temperatures.values(), default=None)
