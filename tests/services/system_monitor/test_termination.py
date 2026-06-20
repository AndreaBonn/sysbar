from collections.abc import Callable

from sysbar.services.system_monitor.termination import ProcessTerminationService


class FakeScheduler:
    def __init__(self) -> None:
        self.jobs: dict[int, Callable[[], bool]] = {}
        self._next = 1

    def schedule(self, seconds: float, callback: Callable[[], bool]) -> int:
        handle = self._next
        self._next += 1
        self.jobs[handle] = callback
        return handle

    def cancel(self, handle: int) -> None:
        self.jobs.pop(handle, None)

    def fire(self, handle: int) -> None:
        # GLib one-shot timeouts are removed once their callback returns; mirror
        # that so a fired fallback frees its slot.
        self.jobs.pop(handle)()


class FakeTerminator:
    def __init__(self, alive: bool = True) -> None:
        self.terminated: list[int] = []
        self.killed: list[int] = []
        self._alive = alive

    def terminate(self, pid: int) -> None:
        self.terminated.append(pid)

    def force_kill(self, pid: int) -> None:
        self.killed.append(pid)

    def is_alive(self, pid: int) -> bool:
        return self._alive


def _service(
    terminator: FakeTerminator | None = None,
) -> tuple[ProcessTerminationService, FakeTerminator, FakeScheduler]:
    terminator = terminator or FakeTerminator()
    scheduler = FakeScheduler()
    service = ProcessTerminationService(terminator=terminator, scheduler=scheduler)
    return service, terminator, scheduler


def test_terminate_sends_sigterm_and_schedules_kill() -> None:
    service, terminator, scheduler = _service()
    service.terminate(4242)
    assert terminator.terminated == [4242]
    assert len(scheduler.jobs) == 1  # SIGKILL fallback scheduled


def test_escalates_to_sigkill_when_still_alive() -> None:
    service, terminator, scheduler = _service(FakeTerminator(alive=True))
    service.terminate(4242)
    scheduler.fire(next(iter(scheduler.jobs)))
    assert terminator.killed == [4242]


def test_no_sigkill_when_process_already_exited() -> None:
    service, terminator, scheduler = _service(FakeTerminator(alive=False))
    service.terminate(4242)
    scheduler.fire(next(iter(scheduler.jobs)))
    assert terminator.killed == []


def test_repeated_terminate_does_not_double_schedule() -> None:
    service, terminator, scheduler = _service()
    service.terminate(4242)
    service.terminate(4242)
    assert terminator.terminated == [4242, 4242]  # SIGTERM resent
    assert len(scheduler.jobs) == 1  # but only one kill fallback pending


def test_kill_fallback_clears_pending_so_next_request_reschedules() -> None:
    service, _terminator, scheduler = _service(FakeTerminator(alive=False))
    service.terminate(4242)
    scheduler.fire(next(iter(scheduler.jobs)))
    service.terminate(4242)
    assert len(scheduler.jobs) == 1  # a fresh fallback after the first resolved
