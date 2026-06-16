from collections.abc import Callable

from sysbar.services.auto_quit.ports import WindowClosedCallback, WindowOpenedCallback
from sysbar.services.auto_quit.service import AutoQuitService


class FakeSource:
    def subscribe(self, on_opened: WindowOpenedCallback, on_closed: WindowClosedCallback) -> None:
        pass


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
        self.jobs[handle]()


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
    scheduler: FakeScheduler | None = None,
    exceptions: list[str] | None = None,
    system_ids: frozenset[str] = frozenset(),
    enabled: bool = True,
) -> tuple[AutoQuitService, FakeTerminator, FakeScheduler]:
    terminator = terminator or FakeTerminator()
    scheduler = scheduler or FakeScheduler()
    service = AutoQuitService(
        source=FakeSource(),
        terminator=terminator,
        scheduler=scheduler,
        exceptions=lambda: list(exceptions or []),
        system_ids=system_ids,
        enabled=lambda: enabled,
    )
    return service, terminator, scheduler


def test_last_window_close_terminates_with_sigterm() -> None:
    service, terminator, scheduler = _service()
    service.handle_window_opened(1, "org.app", pid=4242)
    service.handle_window_closed(1)
    assert len(scheduler.jobs) == 1  # grace scheduled
    scheduler.fire(next(iter(scheduler.jobs)))
    assert terminator.terminated == [4242]


def test_escalates_to_sigkill_when_still_alive() -> None:
    service, terminator, scheduler = _service(terminator=FakeTerminator(alive=True))
    service.handle_window_opened(1, "org.app", pid=4242)
    service.handle_window_closed(1)
    grace = next(iter(scheduler.jobs))
    scheduler.fire(grace)
    kill_handle = next(h for h in scheduler.jobs if h != grace)
    scheduler.fire(kill_handle)
    assert terminator.killed == [4242]


def test_no_sigkill_when_process_already_exited() -> None:
    service, terminator, scheduler = _service(terminator=FakeTerminator(alive=False))
    service.handle_window_opened(1, "org.app", pid=4242)
    service.handle_window_closed(1)
    handles = list(scheduler.jobs)
    scheduler.fire(handles[0])
    scheduler.fire(next(h for h in scheduler.jobs if h not in handles))
    assert terminator.killed == []


def test_excepted_app_is_not_terminated() -> None:
    service, _terminator, scheduler = _service(exceptions=["org.app"])
    service.handle_window_opened(1, "org.app", pid=1)
    service.handle_window_closed(1)
    assert scheduler.jobs == {}


def test_system_app_is_not_terminated() -> None:
    service, _terminator, scheduler = _service(system_ids=frozenset({"gnome-shell"}))
    service.handle_window_opened(1, "gnome-shell", pid=1)
    service.handle_window_closed(1)
    assert scheduler.jobs == {}


def test_terminates_only_after_last_window_closes() -> None:
    service, _terminator, scheduler = _service()
    service.handle_window_opened(1, "org.app", pid=1)
    service.handle_window_opened(2, "org.app", pid=1)
    service.handle_window_closed(1)
    assert scheduler.jobs == {}  # one window still open
    service.handle_window_closed(2)
    assert len(scheduler.jobs) == 1


def test_reopening_during_grace_cancels_termination() -> None:
    service, _terminator, scheduler = _service()
    service.handle_window_opened(1, "org.app", pid=1)
    service.handle_window_closed(1)
    assert len(scheduler.jobs) == 1
    service.handle_window_opened(2, "org.app", pid=1)
    assert scheduler.jobs == {}  # grace canceled


def test_disabled_service_does_not_terminate() -> None:
    service, _terminator, scheduler = _service(enabled=False)
    service.handle_window_opened(1, "org.app", pid=1)
    service.handle_window_closed(1)
    assert scheduler.jobs == {}


def test_no_pid_known_skips_termination() -> None:
    service, _terminator, scheduler = _service()
    service.handle_window_opened(1, "org.app", pid=None)
    service.handle_window_closed(1)
    assert scheduler.jobs == {}
