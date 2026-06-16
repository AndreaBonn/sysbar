from sysbar.services.system_monitor.processes import ProcessUsage, top_by_cpu, top_by_memory

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
