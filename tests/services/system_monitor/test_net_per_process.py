from __future__ import annotations

from sysbar.services.system_monitor.net_per_process import (
    NetRateTracker,
    ProcNetSample,
    parse_ss_output,
    top_by_throughput,
)

_ONE_SOCKET = (
    'tcp ESTAB 0 0 192.168.1.10:50012 140.82.121.4:443 users:(("firefox",pid=2100,fd=80))\n'
    "\t cubic rto:236 bytes_sent:5000 bytes_acked:4800 bytes_received:120000 segs_out:50\n"
)

_TWO_SOCKETS_SAME_PID = (
    'tcp ESTAB 0 0 10.0.0.2:111 1.1.1.1:443 users:(("firefox",pid=2100,fd=80))\n'
    "\t cubic bytes_sent:1000 bytes_received:2000\n"
    'tcp ESTAB 0 0 10.0.0.2:222 2.2.2.2:443 users:(("firefox",pid=2100,fd=81))\n'
    "\t cubic bytes_sent:500 bytes_received:300\n"
)

_NO_PROCESS = (
    "tcp ESTAB 0 0 10.0.0.2:333 3.3.3.3:443\n\t cubic bytes_sent:9999 bytes_received:8888\n"
)

_ACKED_ONLY = (
    'tcp ESTAB 0 0 10.0.0.2:444 4.4.4.4:443 users:(("curl",pid=77,fd=3))\n'
    "\t cubic bytes_acked:700 bytes_received:100\n"
)


def test_parse_single_socket_extracts_process_and_bytes() -> None:
    samples = parse_ss_output(_ONE_SOCKET)
    assert samples == [
        ProcNetSample(pid=2100, name="firefox", bytes_sent=5000, bytes_received=120000)
    ]


def test_parse_sums_bytes_across_sockets_of_one_process() -> None:
    samples = parse_ss_output(_TWO_SOCKETS_SAME_PID)
    assert samples == [
        ProcNetSample(pid=2100, name="firefox", bytes_sent=1500, bytes_received=2300)
    ]


def test_parse_skips_socket_without_a_process() -> None:
    assert parse_ss_output(_NO_PROCESS) == []


def test_parse_falls_back_to_bytes_acked_when_sent_absent() -> None:
    samples = parse_ss_output(_ACKED_ONLY)
    assert samples == [ProcNetSample(pid=77, name="curl", bytes_sent=700, bytes_received=100)]


def test_parse_empty_output_returns_empty() -> None:
    assert parse_ss_output("") == []


def test_tracker_first_update_has_no_rates_without_baseline() -> None:
    tracker = NetRateTracker()
    rates = tracker.update([ProcNetSample(1, "a", 100, 200)], interval=2.0)
    assert rates == []


def test_tracker_computes_rate_from_delta_over_interval() -> None:
    tracker = NetRateTracker()
    tracker.update([ProcNetSample(1, "a", 100, 200)], interval=2.0)
    rates = tracker.update([ProcNetSample(1, "a", 300, 1200)], interval=2.0)
    assert len(rates) == 1
    assert rates[0].pid == 1
    assert rates[0].tx_rate == 100.0  # (300-100)/2
    assert rates[0].rx_rate == 500.0  # (1200-200)/2


def test_tracker_clamps_negative_delta_to_zero() -> None:
    tracker = NetRateTracker()
    tracker.update([ProcNetSample(1, "a", 1000, 1000)], interval=2.0)
    rates = tracker.update([ProcNetSample(1, "a", 10, 10)], interval=2.0)
    assert rates[0].tx_rate == 0.0
    assert rates[0].rx_rate == 0.0


def test_tracker_ignores_non_positive_interval() -> None:
    tracker = NetRateTracker()
    tracker.update([ProcNetSample(1, "a", 100, 200)], interval=2.0)
    assert tracker.update([ProcNetSample(1, "a", 300, 400)], interval=0) == []


def test_top_by_throughput_ranks_and_drops_idle_processes() -> None:
    from sysbar.services.system_monitor.net_per_process import ProcNetRate

    rates = [
        ProcNetRate(1, "idle", 0.0, 0.0),
        ProcNetRate(2, "busy", 100.0, 50.0),
        ProcNetRate(3, "mid", 10.0, 10.0),
    ]
    top = top_by_throughput(rates, limit=2)
    assert [r.pid for r in top] == [2, 3]
