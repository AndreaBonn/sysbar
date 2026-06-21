from sysbar.services.system_monitor import parsers
from sysbar.services.system_monitor.models import PeripheralBattery
from sysbar.services.system_monitor.parsers import CpuSample, MemInfo

_KEYBOARD = {
    "Type": 6,
    "Model": "Logitech K780",
    "Percentage": 80.0,
    "State": 2,
    "PowerSupply": False,
    "IsPresent": True,
}
_HEADSET = {
    "Type": 17,
    "Model": "WH-1000XM4",
    "Percentage": 45.0,
    "State": 1,
    "PowerSupply": False,
    "IsPresent": True,
}
_LAPTOP_BATTERY = {
    "Type": 2,
    "Model": "",
    "Percentage": 95.0,
    "State": 1,
    "PowerSupply": True,
    "IsPresent": True,
}

_STAT = """cpu  100 0 50 800 50 0 0 0 0 0
cpu0 50 0 25 400 25 0 0 0 0 0
intr 123
"""

_MEMINFO = """MemTotal:       16000000 kB
MemFree:         2000000 kB
MemAvailable:    8000000 kB
Buffers:          100000 kB
"""

_NET_DEV = """Inter-|   Receive                    |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets
    lo:    1000      10    0    0    0     0          0         0    1000      10
  eth0:  500000     400    0    0    0     0          0         0   250000     300
"""

_PSI = """some avg10=12.50 avg60=3.00 avg300=1.00 total=123456
full avg10=5.00 avg60=1.00 avg300=0.50 total=12345
"""


def test_parse_cpu_stat_aggregate_and_core() -> None:
    samples = parsers.parse_cpu_stat(_STAT)
    assert samples["cpu"] == CpuSample(total=1000, idle=850)
    assert "cpu0" in samples


def test_parse_cpu_stat_ignores_non_cpu_lines() -> None:
    samples = parsers.parse_cpu_stat(_STAT)
    assert set(samples) == {"cpu", "cpu0"}


def test_cpu_busy_percent_half_load() -> None:
    prev = CpuSample(total=1000, idle=800)
    curr = CpuSample(total=1200, idle=900)
    # delta_total=200, delta_idle=100 -> busy 100/200 = 50%
    assert parsers.cpu_busy_percent(prev, curr) == 50.0


def test_cpu_busy_percent_no_delta_returns_zero() -> None:
    sample = CpuSample(total=1000, idle=800)
    assert parsers.cpu_busy_percent(sample, sample) == 0.0


def test_parse_meminfo_extracts_total_and_available() -> None:
    info = parsers.parse_meminfo(_MEMINFO)
    assert info == MemInfo(total_kb=16000000, available_kb=8000000)


def test_memory_used_percent_half() -> None:
    assert parsers.memory_used_percent(MemInfo(total_kb=16000000, available_kb=8000000)) == 50.0


def test_memory_used_percent_zero_total_is_safe() -> None:
    assert parsers.memory_used_percent(MemInfo(total_kb=0, available_kb=0)) == 0.0


def test_parse_uptime_seconds() -> None:
    assert parsers.parse_uptime("12345.67 9999.00") == 12345.67


def test_parse_net_dev_reads_rx_tx_bytes() -> None:
    counters = parsers.parse_net_dev(_NET_DEV)
    assert counters["eth0"] == (500000, 250000)
    assert counters["lo"] == (1000, 1000)


def test_rate_per_second_computes_throughput() -> None:
    assert parsers.rate_per_second(1000, 3000, 2.0) == 1000.0


def test_rate_per_second_zero_interval_is_safe() -> None:
    assert parsers.rate_per_second(1000, 3000, 0.0) == 0.0


def test_parse_psi_some_avg10() -> None:
    assert parsers.parse_psi_some_avg10(_PSI) == 12.5


def test_parse_psi_returns_none_when_absent() -> None:
    assert parsers.parse_psi_some_avg10("garbage") is None


def test_memory_pressure_level_normal() -> None:
    assert parsers.memory_pressure_level(5.0) == "normal"


def test_memory_pressure_level_warning_at_threshold() -> None:
    assert parsers.memory_pressure_level(10.0) == "warning"


def test_memory_pressure_level_critical_at_threshold() -> None:
    assert parsers.memory_pressure_level(40.0) == "critical"


def test_parse_cpu_stat_skips_lines_with_too_few_fields() -> None:
    # A truncated cpu line (fewer than 5 counters) cannot yield idle, so it is dropped.
    samples = parsers.parse_cpu_stat("cpu 1 2 3\ncpu0 10 0 5 80 5 0\n")
    assert "cpu" not in samples
    assert "cpu0" in samples


def test_parse_meminfo_ignores_non_numeric_lines() -> None:
    text = "MemTotal:       1000 kB\nHugePagesize:   unknown\nMemAvailable:    400 kB\n"
    info = parsers.parse_meminfo(text)
    assert info == MemInfo(total_kb=1000, available_kb=400)


def test_parse_meminfo_absent_fields_default_to_zero() -> None:
    assert parsers.parse_meminfo("") == MemInfo(total_kb=0, available_kb=0)


def test_parse_net_dev_skips_interfaces_with_too_few_columns() -> None:
    counters = parsers.parse_net_dev("  eth0: 1 2 3\n")
    assert counters == {}


def test_parse_psi_some_line_without_avg10_returns_none() -> None:
    assert parsers.parse_psi_some_avg10("some avg60=3.00 avg300=1.00 total=10\n") is None


def test_parse_upower_devices_maps_peripherals() -> None:
    result = parsers.parse_upower_devices([_KEYBOARD, _HEADSET])
    assert result == (
        PeripheralBattery(model="Logitech K780", kind=6, percent=80.0, charging=False),
        PeripheralBattery(model="WH-1000XM4", kind=17, percent=45.0, charging=True),
    )


def test_parse_upower_devices_excludes_power_supply() -> None:
    assert parsers.parse_upower_devices([_LAPTOP_BATTERY]) == ()


def test_parse_upower_devices_excludes_absent_device() -> None:
    absent = {**_KEYBOARD, "IsPresent": False}
    assert parsers.parse_upower_devices([absent]) == ()


def test_parse_upower_devices_excludes_zero_percent() -> None:
    no_reading = {**_HEADSET, "Percentage": 0.0}
    assert parsers.parse_upower_devices([no_reading]) == ()


def test_parse_upower_devices_defaults_missing_fields() -> None:
    minimal = {"Percentage": 50.0}
    assert parsers.parse_upower_devices([minimal]) == (
        PeripheralBattery(model="", kind=0, percent=50.0, charging=False),
    )
