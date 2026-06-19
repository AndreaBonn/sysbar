import logging
import signal

import pytest
from pytest_mock import MockerFixture

from sysbar.services.auto_quit.os_terminator import OsTerminator


def test_is_alive_process_lookup_error_returns_false(mocker: MockerFixture) -> None:
    mocker.patch("sysbar.services.auto_quit.os_terminator.os.kill", side_effect=ProcessLookupError)
    assert OsTerminator().is_alive(4242) is False


def test_is_alive_permission_error_returns_true(mocker: MockerFixture) -> None:
    mocker.patch("sysbar.services.auto_quit.os_terminator.os.kill", side_effect=PermissionError)
    assert OsTerminator().is_alive(4242) is True


def test_is_alive_no_exception_returns_true(mocker: MockerFixture) -> None:
    mocker.patch("sysbar.services.auto_quit.os_terminator.os.kill")
    assert OsTerminator().is_alive(4242) is True


def test_is_alive_probes_with_signal_zero(mocker: MockerFixture) -> None:
    kill = mocker.patch("sysbar.services.auto_quit.os_terminator.os.kill")
    OsTerminator().is_alive(4242)
    kill.assert_called_once_with(4242, 0)


def test_terminate_sends_sigterm(mocker: MockerFixture) -> None:
    kill = mocker.patch("sysbar.services.auto_quit.os_terminator.os.kill")
    OsTerminator().terminate(4242)
    kill.assert_called_once_with(4242, signal.SIGTERM)


def test_force_kill_sends_sigkill(mocker: MockerFixture) -> None:
    kill = mocker.patch("sysbar.services.auto_quit.os_terminator.os.kill")
    OsTerminator().force_kill(4242)
    kill.assert_called_once_with(4242, signal.SIGKILL)


def test_terminate_swallows_process_lookup_error(mocker: MockerFixture) -> None:
    mocker.patch("sysbar.services.auto_quit.os_terminator.os.kill", side_effect=ProcessLookupError)
    OsTerminator().terminate(4242)  # must not raise


def test_force_kill_swallows_process_lookup_error(mocker: MockerFixture) -> None:
    mocker.patch("sysbar.services.auto_quit.os_terminator.os.kill", side_effect=ProcessLookupError)
    OsTerminator().force_kill(4242)  # must not raise


def test_signal_logs_warning_on_permission_error(
    mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    mocker.patch("sysbar.services.auto_quit.os_terminator.os.kill", side_effect=PermissionError)
    with caplog.at_level(logging.WARNING, logger="sysbar.services.auto_quit.os_terminator"):
        OsTerminator().terminate(4242)
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING
    assert caplog.records[0].pid == 4242  # type: ignore[attr-defined]
