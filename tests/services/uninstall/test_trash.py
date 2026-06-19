from gi.repository import GLib
from pytest_mock import MockerFixture

from sysbar.services.uninstall.trash import GioTrash


def test_trash_returns_true_on_success(mocker: MockerFixture) -> None:
    gio_file = mocker.Mock()
    gio_file.trash.return_value = True
    mocker.patch("sysbar.services.uninstall.trash.Gio.File.new_for_path", return_value=gio_file)

    assert GioTrash().trash("/tmp/sysbar-app") is True
    gio_file.trash.assert_called_once_with(None)


def test_trash_returns_false_when_gio_reports_failure(mocker: MockerFixture) -> None:
    gio_file = mocker.Mock()
    gio_file.trash.return_value = False
    mocker.patch("sysbar.services.uninstall.trash.Gio.File.new_for_path", return_value=gio_file)

    assert GioTrash().trash("/tmp/sysbar-app") is False


def test_trash_returns_false_and_logs_on_glib_error(mocker: MockerFixture) -> None:
    gio_file = mocker.Mock()
    gio_file.trash.side_effect = GLib.Error("trash not supported")
    mocker.patch("sysbar.services.uninstall.trash.Gio.File.new_for_path", return_value=gio_file)
    warning = mocker.patch("sysbar.services.uninstall.trash.log.warning")

    assert GioTrash().trash("/tmp/sysbar-app") is False
    warning.assert_called_once()
