import pytest
from pytest_mock import MockerFixture

from sysbar.services.keep_awake.scheduler import GLibScheduler


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0.5, 1), (2.9, 2), (5, 5)],
)
def test_schedule_clamps_and_truncates_seconds(
    mocker: MockerFixture, seconds: float, expected: int
) -> None:
    timeout_add = mocker.patch(
        "sysbar.services.keep_awake.scheduler.GLib.timeout_add_seconds", return_value=7
    )
    scheduler = GLibScheduler()

    def callback() -> bool:
        return False

    handle = scheduler.schedule(seconds, callback)

    assert handle == 7
    timeout_add.assert_called_once_with(expected, callback)


def test_cancel_removes_source(mocker: MockerFixture) -> None:
    source_remove = mocker.patch("sysbar.services.keep_awake.scheduler.GLib.source_remove")
    scheduler = GLibScheduler()

    scheduler.cancel(42)

    source_remove.assert_called_once_with(42)
