import sys
import types

import pytest
from pytest_mock import MockerFixture

from sysbar.services.shelf.shake_detector import ShakeDetector
from sysbar.services.shelf.shake_monitor import ShakeMonitor


class FakePointer:
    def __init__(self, root_x: int, root_y: int) -> None:
        self.root_x = root_x
        self.root_y = root_y


class FakeRoot:
    def __init__(self, positions: list[tuple[int, int]]) -> None:
        self._positions = positions
        self._index = 0

    def query_pointer(self) -> FakePointer:
        x, y = self._positions[min(self._index, len(self._positions) - 1)]
        self._index += 1
        return FakePointer(x, y)


def _monitor(positions: list[tuple[int, int]]) -> ShakeMonitor:
    monitor = ShakeMonitor(on_shake=lambda: None)
    monitor._root = FakeRoot(positions)
    return monitor


def test_tick_returns_false_when_root_unavailable() -> None:
    monitor = ShakeMonitor(on_shake=lambda: None)
    assert monitor._tick() is False


def test_first_tick_does_not_feed_detector(mocker: MockerFixture) -> None:
    monitor = _monitor([(100, 50)])
    feed = mocker.spy(monitor._detector, "feed")

    result = monitor._tick()

    assert result is True
    feed.assert_not_called()
    assert monitor._last == (100, 50)


def test_subsequent_tick_feeds_horizontal_delta(mocker: MockerFixture) -> None:
    monitor = _monitor([(100, 50), (130, 50)])
    monitor._tick()
    feed = mocker.spy(monitor._detector, "feed")

    monitor._tick()

    feed.assert_called_once()
    dx = feed.call_args.args[0]
    assert dx == 30.0


def test_tick_uses_only_horizontal_axis(mocker: MockerFixture) -> None:
    monitor = _monitor([(100, 50), (100, 999)])
    monitor._tick()
    feed = mocker.spy(monitor._detector, "feed")

    monitor._tick()

    assert feed.call_args.args[0] == 0.0


def test_shake_schedules_fire_via_idle_add(mocker: MockerFixture) -> None:
    positions = [(0, 0), (40, 0), (0, 0), (40, 0), (0, 0), (40, 0)]
    monitor = _monitor(positions)
    idle_add = mocker.patch("sysbar.services.shelf.shake_monitor.GLib.idle_add")

    for _ in positions:
        monitor._tick()

    idle_add.assert_called_with(monitor._fire)


def test_no_shake_does_not_schedule_fire(mocker: MockerFixture) -> None:
    positions = [(0, 0), (40, 0), (80, 0), (120, 0)]
    monitor = _monitor(positions)
    idle_add = mocker.patch("sysbar.services.shelf.shake_monitor.GLib.idle_add")

    for _ in positions:
        monitor._tick()

    idle_add.assert_not_called()


def test_stop_resets_state_and_removes_timer(mocker: MockerFixture) -> None:
    remove = mocker.patch("sysbar.services.shelf.shake_monitor.GLib.source_remove")
    monitor = _monitor([(100, 50), (130, 50)])
    monitor._timer = 7
    monitor._tick()
    monitor._tick()

    monitor.stop()

    remove.assert_called_once_with(7)
    assert monitor._timer == 0
    assert monitor._last is None


def test_stop_resets_detector(mocker: MockerFixture) -> None:
    mocker.patch("sysbar.services.shelf.shake_monitor.GLib.source_remove")
    monitor = _monitor([(0, 0)])
    reset = mocker.spy(monitor._detector, "reset")

    monitor.stop()

    reset.assert_called_once()


def test_stop_without_active_timer_does_not_call_source_remove(mocker: MockerFixture) -> None:
    remove = mocker.patch("sysbar.services.shelf.shake_monitor.GLib.source_remove")
    monitor = _monitor([(0, 0)])

    monitor.stop()

    remove.assert_not_called()


def test_fire_invokes_callback_and_returns_false() -> None:
    calls: list[str] = []
    monitor = ShakeMonitor(on_shake=lambda: calls.append("shaken"))

    result = monitor._fire()

    assert calls == ["shaken"]
    assert result is False


def test_detector_is_real_shake_detector() -> None:
    monitor = ShakeMonitor(on_shake=lambda: None)
    assert isinstance(monitor._detector, ShakeDetector)


def test_start_returns_false_when_xlib_import_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A stand-in Xlib module without a ``display`` submodule makes the
    # ``from Xlib import display`` import raise, exercising the failure path.
    fake_xlib = types.ModuleType("Xlib")
    monkeypatch.setitem(sys.modules, "Xlib", fake_xlib)
    monkeypatch.delitem(sys.modules, "Xlib.display", raising=False)
    monitor = ShakeMonitor(on_shake=lambda: None)

    assert monitor.start() is False
    assert monitor._root is None
