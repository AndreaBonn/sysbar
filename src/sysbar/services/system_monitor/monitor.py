"""Observable system monitor service.

Owns a single timer and the stateful sampler, emits ``snapshot-updated`` at the
configured cadence, and suspends sampling when neither the panel is open nor any
tray metric is active (port of ``panelDidAppear``/``setMenuBarActive``).
"""

from __future__ import annotations

import logging
from typing import ClassVar

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib, GObject  # noqa: E402

from ...core.config import Config  # noqa: E402
from .adapters import (  # noqa: E402
    DiskUsageReader,
    GpuReaderChain,
    ProcfsReader,
    PsutilSensorReader,
    SysfsPowerReader,
    UPowerPeripheralReader,
)
from .sampler import SystemSampler  # noqa: E402
from .snapshot import SystemSnapshot  # noqa: E402

log = logging.getLogger(__name__)


class SystemMonitor(GObject.Object):
    """Samples the system on a timer and publishes snapshots."""

    __gsignals__: ClassVar[dict[str, tuple[object, ...]]] = {
        "snapshot-updated": (GObject.SignalFlags.RUN_FIRST, None, (object,))
    }

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config
        self._sampler = SystemSampler(
            ProcfsReader(),
            PsutilSensorReader(),
            GpuReaderChain(),
            SysfsPowerReader(),
            DiskUsageReader(),
            UPowerPeripheralReader(),
        )
        self._timer_id = 0
        self._panel_open = False
        self._tray_active = False
        self._alerting_active = False
        self._latest: SystemSnapshot | None = None

    @property
    def latest(self) -> SystemSnapshot | None:
        return self._latest

    def set_panel_open(self, value: bool) -> None:
        self._panel_open = value
        self._reconcile()

    def set_tray_active(self, value: bool) -> None:
        self._tray_active = value
        self._reconcile()

    def set_alerting_active(self, value: bool) -> None:
        """Keep sampling alive for threshold alerts even when nothing is shown."""
        self._alerting_active = value
        self._reconcile()

    def _reconcile(self) -> None:
        wants_sampling = self._panel_open or self._tray_active or self._alerting_active
        if wants_sampling and not self._timer_id:
            self._start()
        elif not wants_sampling and self._timer_id:
            self._stop()

    def _start(self) -> None:
        self._tick()
        interval = self._config.monitor_interval_seconds
        self._timer_id = GLib.timeout_add_seconds(interval, self._tick)

    def _stop(self) -> None:
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = 0

    def _tick(self) -> bool:
        snapshot = self._sampler.build_snapshot(self._config.monitor_interval_seconds)
        self._latest = snapshot
        self.emit("snapshot-updated", snapshot)
        return True
