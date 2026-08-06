"""System sampling, history, threshold alerts and process listings.

These are one feature because they share one sample: the monitor emits a
snapshot, and the history, the alert engine and the tray all consume that same
value. Splitting them would mean either sampling more than once or passing the
snapshot back and forth across module boundaries.

``latest`` may still be ``None``, but that is data rather than wiring: it means
no sample has arrived yet, and the tray renders an empty label for it.
"""

from __future__ import annotations

from collections.abc import Callable

from ...core.capabilities import PROC_NET_STATS
from ...core.constants import NET_PROCESS_COUNT, TOP_PROCESS_COUNT
from ...services.auto_quit.os_terminator import OsTerminator
from ...services.keep_awake.scheduler import GLibScheduler
from ...services.system_monitor.alerting import AlertEngine, AlertThresholds
from ...services.system_monitor.history import MetricHistory
from ...services.system_monitor.monitor import SystemMonitor
from ...services.system_monitor.net_per_process import (
    NetRateTracker,
    ProcNetRate,
    SsNetSampler,
    top_by_throughput,
)
from ...services.system_monitor.processes import ProcessUsage, ProcessUsageService
from ...services.system_monitor.snapshot import SystemSnapshot
from ...services.system_monitor.termination import ProcessTerminationService
from ..context import AppContext


class MonitorFeature:
    """Owns sampling and everything derived from a sample."""

    def __init__(self, context: AppContext, on_snapshot: Callable[[SystemSnapshot], None]) -> None:
        self._context = context
        self._on_snapshot = on_snapshot
        self._history = MetricHistory()
        self._process_usage = ProcessUsageService()
        self._net_tracker = NetRateTracker()
        self._killer = ProcessTerminationService(OsTerminator(), GLibScheduler())
        self._alerts = AlertEngine(thresholds=self._thresholds)
        self._net_sampler = SsNetSampler() if context.has(PROC_NET_STATS) else None
        self._monitor = SystemMonitor(context.config)
        self._monitor.connect("snapshot-updated", self._handle_snapshot)

    @property
    def latest(self) -> SystemSnapshot | None:
        """The most recent sample, or ``None`` before the first one arrives."""
        return self._monitor.latest

    @property
    def history(self) -> MetricHistory:
        return self._history

    def set_panel_open(self, is_open: bool) -> None:
        self._monitor.set_panel_open(is_open)

    def set_tray_active(self, active: bool) -> None:
        self._monitor.set_tray_active(active)

    def reconcile_alerting(self) -> None:
        """Match the engine's activity to the ``alert-enabled`` setting."""
        self._monitor.set_alerting_active(self._context.config.alert_enabled)

    def top_cpu(self, limit: int = TOP_PROCESS_COUNT) -> list[ProcessUsage]:
        return self._process_usage.top_cpu(limit)

    def net_processes(self) -> list[ProcNetRate]:
        """Bandwidth by process, empty when ``ss`` is unavailable."""
        sampler = self._net_sampler
        if sampler is None:
            return []
        rates = self._net_tracker.update(
            sampler.sample(), self._context.config.monitor_interval_seconds
        )
        return top_by_throughput(rates, NET_PROCESS_COUNT)

    def terminate(self, pid: int) -> None:
        self._killer.terminate(pid)

    def _handle_snapshot(self, _monitor: SystemMonitor, snapshot: SystemSnapshot) -> None:
        self._history.record(snapshot)
        self._raise_alerts(snapshot)
        self._on_snapshot(snapshot)

    def _raise_alerts(self, snapshot: SystemSnapshot) -> None:
        if not self._context.config.alert_enabled:
            return
        for alert in self._alerts.evaluate(snapshot):
            self._context.notifier.notify(
                alert.title, alert.body, notification_id=f"alert-{alert.key}"
            )

    def _thresholds(self) -> AlertThresholds:
        config = self._context.config
        return AlertThresholds(
            cpu_percent=config.alert_cpu_percent,
            cpu_seconds=config.alert_cpu_seconds,
            memory_percent=config.alert_memory_percent,
            disk_percent=config.alert_disk_percent,
            temperature_celsius=config.alert_temperature_celsius,
            battery_percent=config.alert_battery_percent,
        )
