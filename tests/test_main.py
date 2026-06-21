import sys
import types

import pytest
from pytest_mock import MockerFixture

from sysbar import __main__


def test_version_flag_exits() -> None:
    parser = __main__.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--version"])


def test_selftest_flag_is_set() -> None:
    args = __main__.build_parser().parse_args(["--selftest"])
    assert args.selftest is True
    assert args.sensors is False


def test_sensors_flag_is_set() -> None:
    args = __main__.build_parser().parse_args(["--sensors"])
    assert args.sensors is True
    assert args.selftest is False


def test_no_flags_default_unset() -> None:
    args = __main__.build_parser().parse_args([])
    assert args.selftest is False
    assert args.sensors is False


def _install_fake_application(monkeypatch: pytest.MonkeyPatch, app_class: object) -> None:
    # The real ``sysbar.app.application`` requires Gtk 4.0, but the test session
    # may already have Gtk 3.0 loaded (via libwnck). Inject a stand-in module so
    # main()'s lazy import resolves without touching the GTK runtime.
    module = types.ModuleType("sysbar.app.application")
    module.SysbarApplication = app_class  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sysbar.app.application", module)


def test_main_selftest_runs_diagnostic_and_returns_zero(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    mocker.patch("sysbar.core.logging_setup.configure_logging")
    run_selftest = mocker.patch("sysbar.support.selftest.run_selftest", return_value="report")
    app_class = mocker.Mock()
    _install_fake_application(monkeypatch, app_class)

    result = __main__.main(["--selftest"])

    assert result == 0
    run_selftest.assert_called_once_with()
    app_class.assert_not_called()


def test_main_sensors_dumps_and_returns_zero(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    mocker.patch("sysbar.core.logging_setup.configure_logging")
    run_sensors_dump = mocker.patch(
        "sysbar.support.sensors_dump.run_sensors_dump", return_value="dump"
    )
    app_class = mocker.Mock()
    _install_fake_application(monkeypatch, app_class)

    result = __main__.main(["--sensors"])

    assert result == 0
    run_sensors_dump.assert_called_once_with()
    app_class.assert_not_called()


def test_main_default_launches_application(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    mocker.patch("sysbar.core.logging_setup.configure_logging")
    mocker.patch("sysbar.__main__.configure_window_identity")
    app_class = mocker.Mock()
    app_class.return_value.run.return_value = 0
    _install_fake_application(monkeypatch, app_class)

    result = __main__.main([])

    assert result == 0
    app_class.assert_called_once_with()
    app_class.return_value.run.assert_called_once_with(None)


def test_main_default_pins_window_identity_before_launch(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    mocker.patch("sysbar.core.logging_setup.configure_logging")
    identity = mocker.patch("sysbar.__main__.configure_window_identity")
    app_class = mocker.Mock()
    app_class.return_value.run.return_value = 0
    _install_fake_application(monkeypatch, app_class)

    __main__.main([])

    identity.assert_called_once_with()


def test_main_diagnostic_skips_window_identity(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    mocker.patch("sysbar.core.logging_setup.configure_logging")
    mocker.patch("sysbar.support.selftest.run_selftest", return_value="report")
    identity = mocker.patch("sysbar.__main__.configure_window_identity")
    _install_fake_application(monkeypatch, mocker.Mock())

    __main__.main(["--selftest"])

    identity.assert_not_called()


def test_configure_window_identity_sets_prgname_to_app_id(mocker: MockerFixture) -> None:
    from sysbar.core.constants import APP_ID, APP_NAME

    glib = mocker.patch("gi.repository.GLib")

    __main__.configure_window_identity()

    glib.set_prgname.assert_called_once_with(APP_ID)
    glib.set_application_name.assert_called_once_with(APP_NAME)
