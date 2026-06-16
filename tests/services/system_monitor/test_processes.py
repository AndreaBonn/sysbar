from dataclasses import dataclass

import psutil
import pytest

from sysbar.services.system_monitor.processes import (
    ProcessUsage,
    ProcessUsageService,
    top_by_cpu,
    top_by_memory,
)

_PROCESSES = [
    ProcessUsage(pid=1, name="a", cpu_percent=5.0, memory_bytes=300),
    ProcessUsage(pid=2, name="b", cpu_percent=80.0, memory_bytes=100),
    ProcessUsage(pid=3, name="c", cpu_percent=20.0, memory_bytes=900),
]


def test_top_by_cpu_orders_descending() -> None:
    names = [proc.name for proc in top_by_cpu(_PROCESSES)]
    assert names == ["b", "c", "a"]


def test_top_by_cpu_respects_limit() -> None:
    assert [proc.name for proc in top_by_cpu(_PROCESSES, limit=2)] == ["b", "c"]


def test_top_by_memory_orders_descending() -> None:
    names = [proc.name for proc in top_by_memory(_PROCESSES)]
    assert names == ["c", "a", "b"]


def test_top_by_cpu_empty_list() -> None:
    assert top_by_cpu([]) == []


@dataclass
class _Mem:
    rss: int


class _Proc:
    def __init__(self, info: dict[str, object]) -> None:
        self.info = info


def test_collect_maps_psutil_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    procs = [_Proc({"pid": 7, "name": "bash", "cpu_percent": 12.5, "memory_info": _Mem(rss=2048)})]
    monkeypatch.setattr(psutil, "process_iter", lambda _attrs: procs)
    result = ProcessUsageService().collect()
    assert result == [ProcessUsage(pid=7, name="bash", cpu_percent=12.5, memory_bytes=2048)]


def test_collect_defaults_missing_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    # A process that vanished mid-iteration may omit fields or report None values.
    procs = [_Proc({"name": None, "cpu_percent": None, "memory_info": None})]
    monkeypatch.setattr(psutil, "process_iter", lambda _attrs: procs)
    usage = ProcessUsageService().collect()[0]
    assert usage == ProcessUsage(pid=0, name="", cpu_percent=0.0, memory_bytes=0)


def test_top_cpu_collects_then_ranks(monkeypatch: pytest.MonkeyPatch) -> None:
    procs = [
        _Proc({"pid": 1, "name": "a", "cpu_percent": 5.0, "memory_info": _Mem(rss=10)}),
        _Proc({"pid": 2, "name": "b", "cpu_percent": 90.0, "memory_info": _Mem(rss=10)}),
    ]
    monkeypatch.setattr(psutil, "process_iter", lambda _attrs: procs)
    assert [p.name for p in ProcessUsageService().top_cpu(limit=1)] == ["b"]


def test_top_memory_collects_then_ranks(monkeypatch: pytest.MonkeyPatch) -> None:
    procs = [
        _Proc({"pid": 1, "name": "a", "cpu_percent": 5.0, "memory_info": _Mem(rss=10)}),
        _Proc({"pid": 2, "name": "b", "cpu_percent": 5.0, "memory_info": _Mem(rss=9999)}),
    ]
    monkeypatch.setattr(psutil, "process_iter", lambda _attrs: procs)
    assert [p.name for p in ProcessUsageService().top_memory(limit=1)] == ["b"]
