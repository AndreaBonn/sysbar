"""Behaviour of the pure text and level derivations behind the panel rows."""

from __future__ import annotations

from sysbar.app.panel_rows import (
    MetricRow,
    clamp_level,
    fan_subtitle,
    metric_rows,
    net_pair,
    process_row_text,
)
from sysbar.core.constants import TEMPERATURE_CELSIUS, TEMPERATURE_FAHRENHEIT
from sysbar.services.system_monitor.processes import ProcessUsage
from sysbar.services.system_monitor.snapshot import SystemSnapshot

_ROW_KEYS = {
    "cpu",
    "cpu_temp",
    "gpu",
    "memory",
    "uptime",
    "net_speed",
    "net_total",
    "battery",
    "power",
}


def _full_snapshot() -> SystemSnapshot:
    return SystemSnapshot(
        cpu_percent=23.4,
        cpu_temp_celsius=55.4,
        gpu_percent=61.6,
        memory_percent=61.0,
        memory_pressure="warning",
        uptime_seconds=2 * 86400 + 3 * 3600 + 15 * 60 + 40,
        net_rx_rate=2_097_152.0,
        net_tx_rate=512.0,
        net_rx_total=1_073_741_824,
        net_tx_total=2048,
        battery_percent=80.0,
        battery_charging=True,
        power_watts=12.6,
    )


# --- metric_rows ----------------------------------------------------------


def test_metric_rows_empty_snapshot_hides_every_row() -> None:
    rows = metric_rows(SystemSnapshot(), TEMPERATURE_CELSIUS)

    assert set(rows) == _ROW_KEYS
    assert all(row.text is None for row in rows.values())
    assert all(row.level is None for row in rows.values())


def test_metric_rows_full_snapshot_gives_exact_texts() -> None:
    rows = metric_rows(_full_snapshot(), TEMPERATURE_CELSIUS)

    assert {key: row.text for key, row in rows.items()} == {
        "cpu": "23%",
        "cpu_temp": "55°C",
        "gpu": "62%",
        "memory": "61% · high pressure",
        "uptime": "2d 3h 15m",
        "net_speed": "↓2.0 MB/s ↑512 B/s",
        "net_total": "↓1.0 GB ↑2.0 KB",
        "battery": "80% · charging",
        "power": "13 W",
    }


def test_metric_rows_levels_are_the_raw_percentages_of_the_level_rows() -> None:
    rows = metric_rows(_full_snapshot(), TEMPERATURE_CELSIUS)

    assert rows["cpu"] == MetricRow(text="23%", level=23.4)
    assert rows["gpu"].level == 61.6
    assert rows["memory"].level == 61.0
    assert rows["battery"].level == 80.0
    assert rows["uptime"].level is None
    assert rows["power"].level is None


def test_metric_rows_temperature_follows_the_unit() -> None:
    rows = metric_rows(_full_snapshot(), TEMPERATURE_FAHRENHEIT)

    assert rows["cpu_temp"].text == "132°F"


def test_metric_rows_network_needs_both_directions() -> None:
    snapshot = SystemSnapshot(net_rx_rate=100.0, net_tx_rate=None)

    assert metric_rows(snapshot, TEMPERATURE_CELSIUS)["net_speed"].text is None


def test_metric_rows_zero_power_is_shown_not_hidden() -> None:
    rows = metric_rows(SystemSnapshot(power_watts=0.0), TEMPERATURE_CELSIUS)

    assert rows["power"].text == "0 W"


# --- clamp_level ----------------------------------------------------------


def test_clamp_level_caps_above_one_hundred() -> None:
    assert clamp_level(130.0) == 100.0


def test_clamp_level_floors_below_zero() -> None:
    assert clamp_level(-5.0) == 0.0


def test_clamp_level_keeps_values_in_range() -> None:
    assert clamp_level(42.5) == 42.5
    assert clamp_level(0.0) == 0.0
    assert clamp_level(100.0) == 100.0


# --- net_pair -------------------------------------------------------------


def test_net_pair_rate_uses_per_second_units() -> None:
    assert net_pair(1024.0, 0.0, rate=True) == "↓1.0 KB/s ↑0 B/s"


def test_net_pair_total_uses_plain_byte_units() -> None:
    assert net_pair(1024.0, 0.0, rate=False) == "↓1.0 KB ↑0 B"


def test_net_pair_missing_side_is_none() -> None:
    assert net_pair(None, 5.0, rate=True) is None
    assert net_pair(5.0, None, rate=False) is None


# --- process_row_text -----------------------------------------------------


def test_process_row_text_gives_name_and_usage() -> None:
    process = ProcessUsage(pid=7, name="firefox", cpu_percent=18.2, memory_bytes=1_572_864)

    assert process_row_text(process) == ("firefox", "18% CPU · 1.5 MB")


def test_process_row_text_empty_name_falls_back_to_unknown() -> None:
    process = ProcessUsage(pid=7, name="", cpu_percent=0.0, memory_bytes=0)

    assert process_row_text(process) == ("Unknown", "0% CPU · 0 B")


# --- fan_subtitle ---------------------------------------------------------


def test_fan_subtitle_rounds_to_whole_rpm() -> None:
    assert fan_subtitle(1234.6) == "1235 RPM"
