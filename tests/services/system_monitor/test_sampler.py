from sysbar.services.system_monitor.sampler import SystemSampler

_STAT_1 = "cpu  100 0 50 800 50 0 0 0 0 0\ncpu0 100 0 50 800 50 0 0 0 0 0\n"
_STAT_2 = "cpu  200 0 100 900 100 0 0 0 0 0\ncpu0 200 0 100 900 100 0 0 0 0 0\n"
_MEMINFO = "MemTotal: 16000000 kB\nMemAvailable: 8000000 kB\n"
_NET_1 = "  eth0: 1000 0 0 0 0 0 0 0 500 0\n    lo: 5 0 0 0 0 0 0 0 5 0\n"
_NET_2 = "  eth0: 3000 0 0 0 0 0 0 0 1500 0\n    lo: 9 0 0 0 0 0 0 0 9 0\n"
_PSI = "some avg10=45.00 avg60=1 total=1\nfull avg10=1 avg60=1 total=1\n"


class FakeProc:
    def __init__(self) -> None:
        self.stat = _STAT_1
        self.net = _NET_1
        self.psi: str | None = _PSI

    def read_stat(self) -> str:
        return self.stat

    def read_meminfo(self) -> str:
        return _MEMINFO

    def read_uptime(self) -> str:
        return "12345.0 0.0"

    def read_net_dev(self) -> str:
        return self.net

    def read_psi_memory(self) -> str | None:
        return self.psi


class FakeSensors:
    def cpu_temperature(self) -> float | None:
        return 54.0

    def all_temperatures(self) -> dict[str, float]:
        return {"cpu": 54.0}

    def fan_speeds(self) -> dict[str, float]:
        return {"cpu_fan": 1200.0}


class FakeGpu:
    def utilization(self) -> float | None:
        return 30.0

    def temperature(self) -> float | None:
        return None


class FakePower:
    def battery_percent(self) -> float | None:
        return 80.0

    def on_battery(self) -> bool | None:
        return True

    def charging(self) -> bool | None:
        return False

    def power_watts(self) -> float | None:
        return 12.5


def _sampler(proc: FakeProc) -> SystemSampler:
    return SystemSampler(proc, FakeSensors(), FakeGpu(), FakePower())


def test_first_snapshot_has_no_cpu_or_net_rate() -> None:
    snap = _sampler(FakeProc()).build_snapshot(interval_seconds=2.0)
    assert snap.cpu_percent is None
    assert snap.net_rx_rate is None
    assert snap.net_rx_total == 1000  # totals available immediately


def test_second_snapshot_computes_cpu_load() -> None:
    proc = FakeProc()
    sampler = _sampler(proc)
    sampler.build_snapshot(interval_seconds=2.0)
    proc.stat = _STAT_2
    snap = sampler.build_snapshot(interval_seconds=2.0)
    # delta_total=300, delta_idle=150 -> 50%
    assert snap.cpu_percent == 50.0
    assert snap.cpu_per_core == [50.0]


def test_second_snapshot_computes_net_rate_excluding_loopback() -> None:
    proc = FakeProc()
    sampler = _sampler(proc)
    sampler.build_snapshot(interval_seconds=2.0)
    proc.net = _NET_2
    snap = sampler.build_snapshot(interval_seconds=2.0)
    # eth0 rx 1000->3000 over 2s = 1000 B/s; lo excluded
    assert snap.net_rx_rate == 1000.0
    assert snap.net_tx_rate == 500.0


def test_memory_percent_and_pressure() -> None:
    snap = _sampler(FakeProc()).build_snapshot(interval_seconds=2.0)
    assert snap.memory_percent == 50.0
    assert snap.memory_pressure == "critical"


def test_pressure_none_when_psi_unavailable() -> None:
    proc = FakeProc()
    proc.psi = None
    snap = _sampler(proc).build_snapshot(interval_seconds=2.0)
    assert snap.memory_pressure is None


def test_optional_sources_pass_through() -> None:
    snap = _sampler(FakeProc()).build_snapshot(interval_seconds=2.0)
    assert snap.cpu_temp_celsius == 54.0
    assert snap.gpu_percent == 30.0
    assert snap.gpu_temp_celsius is None
    assert snap.battery_percent == 80.0
    assert snap.on_battery is True
    assert snap.power_watts == 12.5


class RaisingSensors:
    def cpu_temperature(self) -> float | None:
        raise OSError("sensor read failed")

    def all_temperatures(self) -> dict[str, float]:
        raise OSError("hwmon unreadable")

    def fan_speeds(self) -> dict[str, float]:
        raise OSError("hwmon unreadable")


class BadMeminfoProc(FakeProc):
    def read_meminfo(self) -> str:
        raise OSError("procfs unreadable")


class BadUptimeProc(FakeProc):
    def read_uptime(self) -> str:
        return "not-a-number"


def test_memory_percent_none_when_meminfo_unreadable() -> None:
    snap = _sampler(BadMeminfoProc()).build_snapshot(interval_seconds=2.0)
    assert snap.memory_percent is None


def test_uptime_none_when_uptime_unparseable() -> None:
    snap = _sampler(BadUptimeProc()).build_snapshot(interval_seconds=2.0)
    assert snap.uptime_seconds is None


def test_temperatures_empty_when_sensor_raises() -> None:
    sampler = SystemSampler(FakeProc(), RaisingSensors(), FakeGpu(), FakePower())
    snap = sampler.build_snapshot(interval_seconds=2.0)
    assert snap.temperatures == {}


def test_fans_empty_when_sensor_raises() -> None:
    sampler = SystemSampler(FakeProc(), RaisingSensors(), FakeGpu(), FakePower())
    snap = sampler.build_snapshot(interval_seconds=2.0)
    assert snap.fans == {}


def test_safe_reader_returns_none_when_source_raises() -> None:
    sampler = SystemSampler(FakeProc(), RaisingSensors(), FakeGpu(), FakePower())
    snap = sampler.build_snapshot(interval_seconds=2.0)
    assert snap.cpu_temp_celsius is None
