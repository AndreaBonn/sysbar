import logging
import subprocess

import pytest
from pytest_mock import MockerFixture

from sysbar.services.uninstall.models import PackageManager
from sysbar.services.uninstall.package_remover import PkexecPackageRemover, _command


def _completed(returncode: int) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout="", stderr="")


def test_command_apt_uses_pkexec_apt_get_purge() -> None:
    assert _command(PackageManager.APT, "gedit") == ["pkexec", "apt-get", "purge", "-y", "gedit"]


def test_command_snap_uses_pkexec_snap_remove_purge() -> None:
    assert _command(PackageManager.SNAP, "vlc") == ["pkexec", "snap", "remove", "--purge", "vlc"]


def test_command_flatpak_uses_user_scope_uninstall() -> None:
    assert _command(PackageManager.FLATPAK, "org.x.App") == [
        "flatpak",
        "uninstall",
        "--delete-data",
        "-y",
        "org.x.App",
    ]


def test_command_manual_returns_none() -> None:
    assert _command(PackageManager.MANUAL, "whatever") is None


def test_remove_unsupported_manager_returns_false_without_subprocess(
    mocker: MockerFixture,
) -> None:
    run = mocker.patch("sysbar.services.uninstall.package_remover.subprocess.run")
    assert PkexecPackageRemover().remove(PackageManager.MANUAL, "app") is False
    run.assert_not_called()


def test_remove_success_returns_true_with_correct_argv(mocker: MockerFixture) -> None:
    run = mocker.patch(
        "sysbar.services.uninstall.package_remover.subprocess.run",
        return_value=_completed(0),
    )
    assert PkexecPackageRemover().remove(PackageManager.APT, "gedit") is True
    assert run.call_args.args[0] == ["pkexec", "apt-get", "purge", "-y", "gedit"]


def test_remove_nonzero_returncode_returns_false(mocker: MockerFixture) -> None:
    mocker.patch(
        "sysbar.services.uninstall.package_remover.subprocess.run",
        return_value=_completed(100),
    )
    assert PkexecPackageRemover().remove(PackageManager.APT, "gedit") is False


def test_remove_nonzero_returncode_logs_warning(
    mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    mocker.patch(
        "sysbar.services.uninstall.package_remover.subprocess.run",
        return_value=_completed(100),
    )
    with caplog.at_level(logging.WARNING, logger="sysbar.services.uninstall.package_remover"):
        PkexecPackageRemover().remove(PackageManager.APT, "gedit")
    assert len(caplog.records) == 1
    assert caplog.records[0].ref == "gedit"  # type: ignore[attr-defined]


def test_remove_file_not_found_returns_false_and_logs(
    mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    mocker.patch(
        "sysbar.services.uninstall.package_remover.subprocess.run",
        side_effect=FileNotFoundError("pkexec"),
    )
    with caplog.at_level(logging.WARNING, logger="sysbar.services.uninstall.package_remover"):
        result = PkexecPackageRemover().remove(PackageManager.APT, "gedit")
    assert result is False
    assert len(caplog.records) == 1


def test_remove_timeout_returns_false_and_logs(
    mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    mocker.patch(
        "sysbar.services.uninstall.package_remover.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="pkexec", timeout=120),
    )
    with caplog.at_level(logging.WARNING, logger="sysbar.services.uninstall.package_remover"):
        result = PkexecPackageRemover().remove(PackageManager.SNAP, "vlc")
    assert result is False
    assert len(caplog.records) == 1
