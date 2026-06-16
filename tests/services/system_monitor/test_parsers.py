from sysbar.services.system_monitor import parsers
from sysbar.services.system_monitor.parsers import CpuSample, MemInfo

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
