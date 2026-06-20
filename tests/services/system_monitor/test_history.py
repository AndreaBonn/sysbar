from __future__ import annotations

from sysbar.services.system_monitor.history import MetricHistory, metric_value
from sysbar.services.system_monitor.snapshot import SystemSnapshot


def test_metric_value_maps_simple_percent_metrics() -> None:
    snap = SystemSnapshot(cpu_percent=12.0, gpu_percent=34.0, memory_percent=56.0)
    assert metric_value(snap, "cpu") == 12.0
    assert metric_value(snap, "gpu") == 34.0
    assert metric_value(snap, "memory") == 56.0


def test_metric_value_network_sums_rx_and_tx() -> None:
    snap = SystemSnapshot(net_rx_rate=1000.0, net_tx_rate=250.0)
    assert metric_value(snap, "network") == 1250.0


def test_metric_value_network_is_none_when_either_rate_missing() -> None:
    assert metric_value(SystemSnapshot(net_rx_rate=10.0), "network") is None
    assert metric_value(SystemSnapshot(net_tx_rate=10.0), "network") is None


def test_metric_value_power_and_battery() -> None:
    snap = SystemSnapshot(power_watts=42.0, battery_percent=88.0)
    assert metric_value(snap, "power") == 42.0
    assert metric_value(snap, "battery") == 88.0


def test_metric_value_absent_metric_returns_none() -> None:
    assert metric_value(SystemSnapshot(), "cpu") is None


def test_metric_value_unknown_metric_returns_none() -> None:
    assert metric_value(SystemSnapshot(cpu_percent=10.0), "nonexistent") is None


def test_record_appends_present_values_in_order() -> None:
    history = MetricHistory()
    history.record(SystemSnapshot(cpu_percent=10.0))
    history.record(SystemSnapshot(cpu_percent=20.0))
    assert history.series("cpu") == (10.0, 20.0)


def test_record_skips_metric_when_value_absent() -> None:
    history = MetricHistory()
    history.record(SystemSnapshot(cpu_percent=10.0))  # no gpu
    history.record(SystemSnapshot(gpu_percent=5.0))  # no cpu
    assert history.series("cpu") == (10.0,)
    assert history.series("gpu") == (5.0,)


def test_ring_buffer_caps_at_max_samples_dropping_oldest() -> None:
    history = MetricHistory(max_samples=3)
    for value in (1.0, 2.0, 3.0, 4.0):
        history.record(SystemSnapshot(cpu_percent=value))
    assert history.series("cpu") == (2.0, 3.0, 4.0)


def test_series_is_empty_for_metric_never_recorded() -> None:
    assert MetricHistory().series("power") == ()


def test_clear_empties_all_series() -> None:
    history = MetricHistory()
    history.record(SystemSnapshot(cpu_percent=10.0, memory_percent=50.0))
    history.clear()
    assert history.series("cpu") == ()
    assert history.series("memory") == ()
