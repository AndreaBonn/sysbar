from sysbar.app.tray_renderer import (
    TrayOptions,
    menu_metric_values,
    render_menu_metrics,
    render_tray_label,
)
from sysbar.services.system_monitor.snapshot import SystemSnapshot

BAR = "bar"
MENU = "menu"


def test_empty_when_no_metrics_opted_in() -> None:
    snap = SystemSnapshot(cpu_percent=23.0)
    assert render_tray_label(snap, TrayOptions()) == ""


def test_cpu_with_temperature() -> None:
    snap = SystemSnapshot(cpu_percent=23.0, cpu_temp_celsius=54.0)
    label = render_tray_label(snap, TrayOptions(cpu=BAR))
    assert label == "CPU 23% · 54°C"


def test_cpu_hides_temperature_when_unavailable() -> None:
    snap = SystemSnapshot(cpu_percent=23.0, cpu_temp_celsius=None)
    assert render_tray_label(snap, TrayOptions(cpu=BAR)) == "CPU 23%"


def test_memory_percent_style() -> None:
    snap = SystemSnapshot(memory_percent=50.0)
    label = render_tray_label(snap, TrayOptions(memory=BAR, memory_style="percent"))
    assert label == "RAM 50%"


def test_network_shows_both_directions() -> None:
    snap = SystemSnapshot(net_rx_rate=2.1 * 1024 * 1024, net_tx_rate=512 * 1024)
    label = render_tray_label(snap, TrayOptions(network=BAR))
    assert label == "↓2.1 MB/s ↑512.0 KB/s"


def test_multiple_metrics_joined() -> None:
    snap = SystemSnapshot(cpu_percent=23.0, gpu_percent=30.0)
    label = render_tray_label(snap, TrayOptions(cpu=BAR, gpu=BAR))
    assert label == "CPU 23% · GPU 30%"


def test_fahrenheit_unit() -> None:
    snap = SystemSnapshot(cpu_percent=10.0, cpu_temp_celsius=100.0)
    label = render_tray_label(snap, TrayOptions(cpu=BAR, temperature_unit="fahrenheit"))
    assert label == "CPU 10% · 212°F"


def test_power_segment() -> None:
    snap = SystemSnapshot(power_watts=12.0)
    assert render_tray_label(snap, TrayOptions(power=BAR)) == "12 W"


def test_battery_segment() -> None:
    snap = SystemSnapshot(battery_percent=88.0)
    assert render_tray_label(snap, TrayOptions(battery=BAR)) == "BAT 88%"


def test_battery_hidden_when_unavailable() -> None:
    snap = SystemSnapshot(battery_percent=None)
    assert render_tray_label(snap, TrayOptions(battery=BAR)) == ""


def test_gpu_hidden_when_unavailable() -> None:
    snap = SystemSnapshot(gpu_percent=None)
    assert render_tray_label(snap, TrayOptions(gpu=BAR)) == ""


def test_power_hidden_when_unavailable() -> None:
    snap = SystemSnapshot(power_watts=None)
    assert render_tray_label(snap, TrayOptions(power=BAR)) == ""


def test_cpu_shows_temperature_only_when_percent_missing() -> None:
    snap = SystemSnapshot(cpu_percent=None, cpu_temp_celsius=60.0)
    assert render_tray_label(snap, TrayOptions(cpu=BAR)) == "60°C"


def test_memory_hidden_when_percent_missing() -> None:
    snap = SystemSnapshot(memory_percent=None)
    assert render_tray_label(snap, TrayOptions(memory=BAR)) == ""


def test_memory_dot_style_shows_pressure_dot_only() -> None:
    snap = SystemSnapshot(memory_percent=50.0, memory_pressure="warning")
    assert render_tray_label(snap, TrayOptions(memory=BAR, memory_style="dot")) == "●"


def test_memory_both_style_shows_dot_and_percent() -> None:
    snap = SystemSnapshot(memory_percent=50.0, memory_pressure="normal")
    assert render_tray_label(snap, TrayOptions(memory=BAR, memory_style="both")) == "● 50%"


def test_network_hidden_when_rates_missing() -> None:
    snap = SystemSnapshot(net_rx_rate=None, net_tx_rate=None)
    assert render_tray_label(snap, TrayOptions(network=BAR)) == ""


def test_bar_label_ignores_menu_metrics() -> None:
    snap = SystemSnapshot(cpu_percent=23.0, gpu_percent=30.0)
    label = render_tray_label(snap, TrayOptions(cpu=BAR, gpu=MENU))
    assert label == "CPU 23%"


def test_menu_metrics_empty_when_none_assigned() -> None:
    snap = SystemSnapshot(cpu_percent=23.0)
    assert render_menu_metrics(snap, TrayOptions(cpu=BAR)) == []


def test_menu_metrics_returns_one_line_per_metric() -> None:
    snap = SystemSnapshot(cpu_percent=23.0, cpu_temp_celsius=54.0, memory_percent=50.0)
    lines = render_menu_metrics(snap, TrayOptions(cpu=MENU, memory=MENU))
    assert lines == ["CPU 23% · 54°C", "RAM 50%"]


def test_menu_metrics_ignores_bar_metrics() -> None:
    snap = SystemSnapshot(cpu_percent=23.0, gpu_percent=30.0)
    lines = render_menu_metrics(snap, TrayOptions(cpu=BAR, gpu=MENU))
    assert lines == ["GPU 30%"]


def test_menu_metrics_skips_unavailable_metric() -> None:
    snap = SystemSnapshot(battery_percent=None, power_watts=12.0)
    lines = render_menu_metrics(snap, TrayOptions(battery=MENU, power=MENU))
    assert lines == ["12 W"]


def test_menu_metrics_preserve_declared_order() -> None:
    snap = SystemSnapshot(cpu_percent=10.0, power_watts=5.0)
    lines = render_menu_metrics(snap, TrayOptions(power=MENU, cpu=MENU))
    assert lines == ["CPU 10%", "5 W"]


def test_menu_metric_values_maps_metric_id_to_line() -> None:
    snap = SystemSnapshot(cpu_percent=23.0, battery_percent=99.0)
    values = menu_metric_values(snap, TrayOptions(cpu=MENU, battery=MENU))
    assert values == {"cpu": "CPU 23%", "battery": "BAT 99%"}


def test_menu_metric_values_skips_bar_and_empty() -> None:
    snap = SystemSnapshot(cpu_percent=23.0, gpu_percent=30.0, battery_percent=None)
    values = menu_metric_values(snap, TrayOptions(cpu=BAR, gpu=MENU, battery=MENU))
    assert values == {"gpu": "GPU 30%"}


def test_menu_metric_values_follows_tray_metrics_order() -> None:
    snap = SystemSnapshot(cpu_percent=10.0, power_watts=5.0)
    values = menu_metric_values(snap, TrayOptions(power=MENU, cpu=MENU))
    assert list(values.keys()) == ["cpu", "power"]
