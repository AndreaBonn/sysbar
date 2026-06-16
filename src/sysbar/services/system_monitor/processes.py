"""Processes responsible for resource usage (port of ``ProcessUsageService``).

Ranking is a pure function tested with concrete inputs; collection from
``psutil`` is the boundary.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...core.constants import TOP_PROCESS_COUNT


@dataclass(frozen=True)
class ProcessUsage:
    """One process's resource usage."""

    pid: int
    name: str
    cpu_percent: float
    memory_bytes: int


def top_by_cpu(processes: list[ProcessUsage], limit: int = TOP_PROCESS_COUNT) -> list[ProcessUsage]:
    """Return the ``limit`` processes with the highest CPU usage."""
    return sorted(processes, key=lambda proc: proc.cpu_percent, reverse=True)[:limit]


def top_by_memory(
    processes: list[ProcessUsage], limit: int = TOP_PROCESS_COUNT
) -> list[ProcessUsage]:
    """Return the ``limit`` processes with the highest memory usage."""
    return sorted(processes, key=lambda proc: proc.memory_bytes, reverse=True)[:limit]


class ProcessUsageService:
    """Collects per-process usage via ``psutil``."""

    def collect(self) -> list[ProcessUsage]:
        import psutil

        result: list[ProcessUsage] = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            info = proc.info
            memory = info.get("memory_info")
            result.append(
                ProcessUsage(
                    pid=info.get("pid", 0),
                    name=info.get("name") or "",
                    cpu_percent=info.get("cpu_percent") or 0.0,
                    memory_bytes=memory.rss if memory is not None else 0,
                )
            )
        return result

    def top_cpu(self, limit: int = TOP_PROCESS_COUNT) -> list[ProcessUsage]:
        return top_by_cpu(self.collect(), limit)

    def top_memory(self, limit: int = TOP_PROCESS_COUNT) -> list[ProcessUsage]:
        return top_by_memory(self.collect(), limit)
