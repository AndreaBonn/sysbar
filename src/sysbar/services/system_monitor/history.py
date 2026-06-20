"""Rolling per-metric history for the panel sparklines.

A bounded ring buffer of recent values per graphable metric. Pure and
framework-agnostic: the panel reads the series and draws them with Cairo, while
the application feeds snapshots in as they arrive from the monitor.
"""

from __future__ import annotations

from collections import deque

from ...core.constants import GRAPH_METRICS, HISTORY_MAX_SAMPLES
from .snapshot import SystemSnapshot


def metric_value(snapshot: SystemSnapshot, metric: str) -> float | None:
    """Return the scalar a metric contributes to its sparkline, or ``None``.

    ``None`` means the value is unavailable in this snapshot, so no point is
    recorded and the series keeps its previous shape. ``network`` collapses the
    receive and transmit rates into a single throughput value.
    """
    match metric:
        case "cpu":
            return snapshot.cpu_percent
        case "gpu":
            return snapshot.gpu_percent
        case "memory":
            return snapshot.memory_percent
        case "power":
            return snapshot.power_watts
        case "battery":
            return snapshot.battery_percent
        case "network":
            if snapshot.net_rx_rate is None or snapshot.net_tx_rate is None:
                return None
            return snapshot.net_rx_rate + snapshot.net_tx_rate
        case _:
            return None


class MetricHistory:
    """Bounded recent-value series for each graphable metric."""

    def __init__(self, max_samples: int = HISTORY_MAX_SAMPLES) -> None:
        self._series: dict[str, deque[float]] = {
            metric: deque(maxlen=max_samples) for metric in GRAPH_METRICS
        }

    def record(self, snapshot: SystemSnapshot) -> None:
        """Append each metric's current value, skipping the unavailable ones."""
        for metric, series in self._series.items():
            value = metric_value(snapshot, metric)
            if value is not None:
                series.append(value)

    def series(self, metric: str) -> tuple[float, ...]:
        """Return the recorded values for ``metric``, oldest first."""
        return tuple(self._series.get(metric, ()))

    def clear(self) -> None:
        for series in self._series.values():
            series.clear()
