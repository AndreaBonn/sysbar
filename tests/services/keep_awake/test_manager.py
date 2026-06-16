from collections.abc import Callable
from datetime import datetime, timedelta

from sysbar.services.keep_awake.manager import WHAT_IDLE_SLEEP, WHAT_LID, KeepAwakeManager
from sysbar.services.keep_awake.ports import EndReason


class FakeInhibitor:
    def __init__(self) -> None:
        self.acquired: list[str] = []
        self.live: set[object] = set()
        self._next = 0

    def acquire(self, what: str) -> object:
        self.acquired.append(what)
        token = self._next
        self._next += 1
        self.live.add(token)
        return token

    def release(self, token: object) -> None:
        self.live.discard(token)


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


class FakeBattery:
    def __init__(self, percent: float | None = 50.0, on_battery: bool | None = False) -> None:
        self._percent = percent
        self._on_battery = on_battery

    def battery_percent(self) -> float | None:
        return self._percent

    def on_battery(self) -> bool | None:
        return self._on_battery


class _Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 1, 1, 12, 0, 0)

    def __call__(self) -> datetime:
        return self.now


def _manager(
    inhibitor: FakeInhibitor | None = None,
    scheduler: FakeScheduler | None = None,
    battery: FakeBattery | None = None,
    clock: Callable[[], datetime] | None = None,
) -> tuple[KeepAwakeManager, FakeInhibitor, FakeScheduler]:
    inhibitor = inhibitor or FakeInhibitor()
    scheduler = scheduler or FakeScheduler()
    manager = KeepAwakeManager(inhibitor, battery or FakeBattery(), scheduler, clock)
    return manager, inhibitor, scheduler


def test_start_activates_and_acquires_sleep_inhibition() -> None:
    manager, inhibitor, _ = _manager()
    manager.start(duration_minutes=0, clamshell=False, battery_limit=0)
    assert manager.is_active is True
    assert inhibitor.acquired == [WHAT_IDLE_SLEEP]
    assert len(inhibitor.live) == 1


def test_clamshell_acquires_lid_inhibition() -> None:
    manager, inhibitor, _ = _manager()
    manager.start(duration_minutes=0, clamshell=True, battery_limit=0)
    assert inhibitor.acquired == [WHAT_IDLE_SLEEP, WHAT_LID]


def test_indefinite_session_has_no_end_date() -> None:
    manager, _, scheduler = _manager()
    manager.start(duration_minutes=0, clamshell=False, battery_limit=0)
    assert manager.end_date is None
    assert manager.remaining_seconds() is None
    assert scheduler.jobs == {}


def test_timed_session_sets_remaining_seconds() -> None:
    clock = _Clock()
    manager, _, _ = _manager(clock=clock)
    manager.start(duration_minutes=30, clamshell=False, battery_limit=0)
    assert manager.end_date == datetime(2026, 1, 1, 12, 30, 0)
    clock.now += timedelta(minutes=10)
    assert manager.remaining_seconds() == 20 * 60


def test_timer_expiry_stops_with_timer_reason() -> None:
    manager, inhibitor, scheduler = _manager()
    reasons: list[str] = []
    manager.connect("session-ended", lambda _m, reason: reasons.append(reason))
    manager.start(duration_minutes=15, clamshell=False, battery_limit=0)
    timer_handle = next(iter(scheduler.jobs))
    scheduler.fire(timer_handle)
    assert manager.is_active is False
    assert reasons == [EndReason.TIMER.value]
    assert inhibitor.live == set()


def test_stop_releases_inhibitions_and_emits() -> None:
    manager, inhibitor, _ = _manager()
    changes: list[bool] = []
    manager.connect("changed", lambda _m: changes.append(True))
    manager.start(duration_minutes=0, clamshell=False, battery_limit=0)
    manager.stop(EndReason.MANUAL)
    assert manager.is_active is False
    assert inhibitor.live == set()
    assert len(changes) == 2  # start + stop


def test_toggle_starts_then_stops() -> None:
    manager, _, _ = _manager()
    manager.toggle(duration_minutes=0, clamshell=False, battery_limit=0)
    assert manager.is_active is True
    manager.toggle(duration_minutes=0, clamshell=False, battery_limit=0)
    assert manager.is_active is False


def test_battery_watchdog_stops_when_below_limit_on_battery() -> None:
    battery = FakeBattery(percent=5.0, on_battery=True)
    manager, _, scheduler = _manager(battery=battery)
    reasons: list[str] = []
    manager.connect("session-ended", lambda _m, reason: reasons.append(reason))
    manager.start(duration_minutes=0, clamshell=False, battery_limit=10)
    battery_handle = next(iter(scheduler.jobs))
    scheduler.fire(battery_handle)
    assert manager.is_active is False
    assert reasons == [EndReason.BATTERY.value]


def test_battery_watchdog_keeps_running_when_above_limit() -> None:
    battery = FakeBattery(percent=50.0, on_battery=True)
    manager, _, scheduler = _manager(battery=battery)
    manager.start(duration_minutes=0, clamshell=False, battery_limit=10)
    battery_handle = next(iter(scheduler.jobs))
    scheduler.fire(battery_handle)
    assert manager.is_active is True


def test_no_battery_watchdog_when_limit_zero() -> None:
    manager, _, scheduler = _manager(battery=FakeBattery(percent=5.0, on_battery=True))
    manager.start(duration_minutes=0, clamshell=False, battery_limit=0)
    assert scheduler.jobs == {}


def test_restart_releases_previous_inhibitions() -> None:
    manager, inhibitor, _ = _manager()
    manager.start(duration_minutes=0, clamshell=False, battery_limit=0)
    manager.start(duration_minutes=0, clamshell=False, battery_limit=0)
    assert len(inhibitor.live) == 1  # old token released, one new held


def test_stop_when_inactive_is_noop() -> None:
    manager, _, _ = _manager()
    changes: list[bool] = []
    manager.connect("changed", lambda _m: changes.append(True))
    manager.stop(EndReason.MANUAL)
    assert manager.is_active is False
    assert changes == []


def test_battery_watchdog_keeps_running_on_ac_power() -> None:
    # On AC power the low charge is irrelevant; the session must continue.
    battery = FakeBattery(percent=2.0, on_battery=False)
    manager, _, scheduler = _manager(battery=battery)
    manager.start(duration_minutes=0, clamshell=False, battery_limit=10)
    scheduler.fire(next(iter(scheduler.jobs)))
    assert manager.is_active is True


class NullInhibitor:
    def __init__(self) -> None:
        self.released: list[object] = []

    def acquire(self, what: str) -> object | None:
        return None

    def release(self, token: object) -> None:
        self.released.append(token)


def test_unavailable_inhibitor_holds_no_tokens() -> None:
    manager, _, _ = _manager(inhibitor=NullInhibitor())  # type: ignore[arg-type]
    manager.start(duration_minutes=0, clamshell=True, battery_limit=0)
    assert manager.is_active is True
    manager.stop(EndReason.MANUAL)  # nothing to release, must not raise


def test_manual_stop_cancels_pending_timers() -> None:
    manager, _, scheduler = _manager()
    manager.start(duration_minutes=15, clamshell=False, battery_limit=10)
    assert len(scheduler.jobs) == 2  # duration timer + battery watchdog
    manager.stop(EndReason.MANUAL)
    assert scheduler.jobs == {}
