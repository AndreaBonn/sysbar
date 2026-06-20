"""Per-process network throughput, best-effort, from ``ss`` (inet_diag).

Linux exposes byte counters per socket, not per process, and ``/proc/<pid>/net``
is per network-namespace, not per task. The pragmatic, unprivileged source is
``ss -tunpi``: it lists each socket's owning process and its ``bytes_sent`` /
``bytes_received`` counters, which we aggregate per pid and differentiate over
time into a rate.

This is approximate: per-socket counters reset as sockets churn, so a process's
summed counter is not strictly monotonic. Negative deltas are clamped to zero,
giving a usable "who is using the network right now" ranking rather than exact
accounting. Parsing and rate maths are pure and unit-tested; the ``ss`` call is
the boundary.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from ...core.constants import SS_COMMAND

_USERS_RE = re.compile(r'users:\(\("(?P<name>[^"]+)",pid=(?P<pid>\d+)')
_SENT_RE = re.compile(r"bytes_sent:(\d+)")
_ACKED_RE = re.compile(r"bytes_acked:(\d+)")
_RECEIVED_RE = re.compile(r"bytes_received:(\d+)")


@dataclass(frozen=True)
class ProcNetSample:
    """Cumulative byte counters attributed to one process at a point in time."""

    pid: int
    name: str
    bytes_sent: int
    bytes_received: int


@dataclass(frozen=True)
class ProcNetRate:
    """A process's instantaneous send/receive throughput, in bytes per second."""

    pid: int
    name: str
    rx_rate: float
    tx_rate: float


def parse_ss_output(text: str) -> list[ProcNetSample]:
    """Aggregate ``ss -tunpi`` output into one cumulative sample per process.

    Each socket spans a header line (carrying ``users:((...))``) followed by an
    indented info line (carrying the byte counters). The current process is
    tracked across lines so the counters land on the right pid; sockets without
    an owning process are ignored.
    """
    totals: dict[int, list[int]] = {}
    names: dict[int, str] = {}
    current_pid: int | None = None
    for line in text.splitlines():
        match = _USERS_RE.search(line)
        if match:
            current_pid = int(match.group("pid"))
            names[current_pid] = match.group("name")
            totals.setdefault(current_pid, [0, 0])
        if current_pid is None:
            continue
        sent = _SENT_RE.search(line) or _ACKED_RE.search(line)
        received = _RECEIVED_RE.search(line)
        if sent:
            totals[current_pid][0] += int(sent.group(1))
        if received:
            totals[current_pid][1] += int(received.group(1))
    return [
        ProcNetSample(pid=pid, name=names[pid], bytes_sent=sent, bytes_received=received)
        for pid, (sent, received) in totals.items()
    ]


def top_by_throughput(rates: list[ProcNetRate], limit: int) -> list[ProcNetRate]:
    """Return the ``limit`` busiest processes, dropping idle ones."""
    active = [rate for rate in rates if rate.rx_rate > 0 or rate.tx_rate > 0]
    active.sort(key=lambda rate: rate.rx_rate + rate.tx_rate, reverse=True)
    return active[:limit]


class NetRateTracker:
    """Differentiates successive cumulative samples into per-process rates.

    Pure and stateful: it remembers the previous sample so the boundary collector
    can stay a thin wrapper. Only processes seen in two consecutive samples get a
    rate; negative deltas (counter churn) are clamped to zero.
    """

    def __init__(self) -> None:
        self._previous: dict[int, ProcNetSample] = {}

    def update(self, current: list[ProcNetSample], interval: float) -> list[ProcNetRate]:
        rates: list[ProcNetRate] = []
        if interval > 0:
            for sample in current:
                previous = self._previous.get(sample.pid)
                if previous is None:
                    continue
                rates.append(
                    ProcNetRate(
                        pid=sample.pid,
                        name=sample.name,
                        rx_rate=max(
                            0.0, (sample.bytes_received - previous.bytes_received) / interval
                        ),
                        tx_rate=max(0.0, (sample.bytes_sent - previous.bytes_sent) / interval),
                    )
                )
        self._previous = {sample.pid: sample for sample in current}
        return rates


class SsNetSampler:  # pragma: no cover - subprocess boundary
    """Collects per-process byte counters by invoking ``ss``."""

    def sample(self) -> list[ProcNetSample]:
        result = subprocess.run(list(SS_COMMAND), capture_output=True, text=True, check=False)
        return parse_ss_output(result.stdout)
