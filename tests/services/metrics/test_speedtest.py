from sysbar.services.metrics.speedtest import throughput_mbps


def test_throughput_one_megabyte_per_second() -> None:
    # 1_000_000 bytes in 1 s = 8 Mbit/s
    assert throughput_mbps(1_000_000, 1.0) == 8.0


def test_throughput_scales_with_time() -> None:
    assert throughput_mbps(1_000_000, 2.0) == 4.0


def test_throughput_zero_seconds_is_safe() -> None:
    assert throughput_mbps(1_000_000, 0.0) == 0.0


def test_throughput_zero_bytes() -> None:
    assert throughput_mbps(0, 1.0) == 0.0
