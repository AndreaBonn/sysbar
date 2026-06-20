from typing import cast

from pytest_mock import MockerFixture

from sysbar.services.system_monitor.monitor import SystemMonitor


class FakeConfig:
    monitor_interval_seconds = 3


class FakeSampler:
    def __init__(self, snapshot: object = "snap") -> None:
        self.snapshot = snapshot
        self.calls: list[float] = []

    def build_snapshot(self, interval_seconds: float) -> object:
        self.calls.append(interval_seconds)
        return self.snapshot


def _monitor() -> SystemMonitor:
    monitor = SystemMonitor(FakeConfig())  # type: ignore[arg-type]
    monitor._sampler = FakeSampler()  # type: ignore[assignment]
    return monitor


def test_set_panel_open_starts_timer(mocker: MockerFixture) -> None:
    timeout = mocker.patch(
        "sysbar.services.system_monitor.monitor.GLib.timeout_add_seconds", return_value=42
    )
    monitor = _monitor()

    monitor.set_panel_open(True)

    timeout.assert_called_once()
    assert monitor._timer_id == 42


def test_set_panel_open_passes_configured_interval(mocker: MockerFixture) -> None:
    timeout = mocker.patch(
        "sysbar.services.system_monitor.monitor.GLib.timeout_add_seconds", return_value=42
    )
    monitor = _monitor()

    monitor.set_panel_open(True)

    assert timeout.call_args.args[0] == 3


def test_set_panel_open_idempotent_does_not_start_second_timer(mocker: MockerFixture) -> None:
    timeout = mocker.patch(
        "sysbar.services.system_monitor.monitor.GLib.timeout_add_seconds", return_value=42
    )
    monitor = _monitor()

    monitor.set_panel_open(True)
    monitor.set_panel_open(True)

    timeout.assert_called_once()


def test_panel_close_stops_timer(mocker: MockerFixture) -> None:
    mocker.patch("sysbar.services.system_monitor.monitor.GLib.timeout_add_seconds", return_value=42)
    remove = mocker.patch("sysbar.services.system_monitor.monitor.GLib.source_remove")
    monitor = _monitor()
    monitor.set_panel_open(True)

    monitor.set_panel_open(False)

    remove.assert_called_once_with(42)
    assert monitor._timer_id == 0


def test_stop_not_called_when_already_inactive(mocker: MockerFixture) -> None:
    remove = mocker.patch("sysbar.services.system_monitor.monitor.GLib.source_remove")
    monitor = _monitor()

    monitor.set_panel_open(False)

    remove.assert_not_called()


def test_tray_active_keeps_timer_when_panel_closes(mocker: MockerFixture) -> None:
    timeout = mocker.patch(
        "sysbar.services.system_monitor.monitor.GLib.timeout_add_seconds", return_value=42
    )
    remove = mocker.patch("sysbar.services.system_monitor.monitor.GLib.source_remove")
    monitor = _monitor()
    monitor.set_panel_open(True)
    monitor.set_tray_active(True)

    monitor.set_panel_open(False)

    timeout.assert_called_once()
    remove.assert_not_called()
    assert monitor._timer_id == 42


def test_timer_stops_only_when_both_sources_inactive(mocker: MockerFixture) -> None:
    mocker.patch("sysbar.services.system_monitor.monitor.GLib.timeout_add_seconds", return_value=42)
    remove = mocker.patch("sysbar.services.system_monitor.monitor.GLib.source_remove")
    monitor = _monitor()
    monitor.set_panel_open(True)
    monitor.set_tray_active(True)

    monitor.set_panel_open(False)
    monitor.set_tray_active(False)

    remove.assert_called_once_with(42)


def test_set_tray_active_idempotent_does_not_double_start(mocker: MockerFixture) -> None:
    timeout = mocker.patch(
        "sysbar.services.system_monitor.monitor.GLib.timeout_add_seconds", return_value=42
    )
    monitor = _monitor()

    monitor.set_tray_active(True)
    monitor.set_tray_active(True)

    timeout.assert_called_once()


def test_alerting_active_starts_sampling_with_panel_closed(mocker: MockerFixture) -> None:
    timeout = mocker.patch(
        "sysbar.services.system_monitor.monitor.GLib.timeout_add_seconds", return_value=42
    )
    monitor = _monitor()

    monitor.set_alerting_active(True)

    timeout.assert_called_once()
    assert monitor._timer_id == 42


def test_alerting_active_keeps_timer_when_panel_and_tray_inactive(mocker: MockerFixture) -> None:
    mocker.patch("sysbar.services.system_monitor.monitor.GLib.timeout_add_seconds", return_value=42)
    remove = mocker.patch("sysbar.services.system_monitor.monitor.GLib.source_remove")
    monitor = _monitor()
    monitor.set_panel_open(True)
    monitor.set_alerting_active(True)

    monitor.set_panel_open(False)

    remove.assert_not_called()
    assert monitor._timer_id == 42


def test_tick_samples_stores_latest_and_returns_true(mocker: MockerFixture) -> None:
    mocker.patch("sysbar.services.system_monitor.monitor.GLib.timeout_add_seconds")
    monitor = _monitor()
    sampler = cast("FakeSampler", monitor._sampler)

    result = monitor._tick()

    assert result is True
    assert cast("object", monitor.latest) == "snap"
    assert sampler.calls == [3]


def test_tick_emits_snapshot_updated_signal(mocker: MockerFixture) -> None:
    mocker.patch("sysbar.services.system_monitor.monitor.GLib.timeout_add_seconds")
    monitor = _monitor()
    received: list[object] = []
    monitor.connect("snapshot-updated", lambda _src, snap: received.append(snap))

    monitor._tick()

    assert received == ["snap"]


def test_start_runs_immediate_tick(mocker: MockerFixture) -> None:
    mocker.patch("sysbar.services.system_monitor.monitor.GLib.timeout_add_seconds", return_value=42)
    monitor = _monitor()

    monitor.set_panel_open(True)

    assert cast("object", monitor.latest) == "snap"


def test_latest_is_none_before_any_sampling() -> None:
    monitor = _monitor()
    assert monitor.latest is None


def test_stop_with_no_active_timer_is_noop(mocker: MockerFixture) -> None:
    remove = mocker.patch("sysbar.services.system_monitor.monitor.GLib.source_remove")
    monitor = _monitor()

    monitor._stop()

    remove.assert_not_called()
    assert monitor._timer_id == 0
