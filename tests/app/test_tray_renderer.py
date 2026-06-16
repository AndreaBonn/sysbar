from sysbar.app.tray_renderer import TrayOptions, render_tray_label
from sysbar.services.system_monitor.snapshot import SystemSnapshot


def test_empty_when_no_metrics_opted_in() -> None:
    snap = SystemSnapshot(cpu_percent=23.0)
    assert render_tray_label(snap, TrayOptions()) == ""


def test_cpu_with_temperature() -> None:
    snap = SystemSnapshot(cpu_percent=23.0, cpu_temp_celsius=54.0)
    label = render_tray_label(snap, TrayOptions(show_cpu=True))
    assert label == "CPU 23% · 54°C"


def test_cpu_hides_temperature_when_unavailable() -> None:
    snap = SystemSnapshot(cpu_percent=23.0, cpu_temp_celsius=None)
    assert render_tray_label(snap, TrayOptions(show_cpu=True)) == "CPU 23%"


def test_memory_percent_style() -> None:
    snap = SystemSnapshot(memory_percent=50.0)
    label = render_tray_label(snap, TrayOptions(show_memory=True, memory_style="percent"))
    assert label == "RAM 50%"


def test_network_shows_both_directions() -> None:
    snap = SystemSnapshot(net_rx_rate=2.1 * 1024 * 1024, net_tx_rate=512 * 1024)
    label = render_tray_label(snap, TrayOptions(show_network=True))
    assert label == "↓2.1 MB/s ↑512.0 KB/s"


def test_multiple_metrics_joined() -> None:
    snap = SystemSnapshot(cpu_percent=23.0, gpu_percent=30.0)
    label = render_tray_label(snap, TrayOptions(show_cpu=True, show_gpu=True))
    assert label == "CPU 23% · GPU 30%"


def test_fahrenheit_unit() -> None:
    snap = SystemSnapshot(cpu_percent=10.0, cpu_temp_celsius=100.0)
    label = render_tray_label(snap, TrayOptions(show_cpu=True, temperature_unit="fahrenheit"))
    assert label == "CPU 10% · 212°F"


def test_power_segment() -> None:
    snap = SystemSnapshot(power_watts=12.0)
    assert render_tray_label(snap, TrayOptions(show_power=True)) == "12 W"
