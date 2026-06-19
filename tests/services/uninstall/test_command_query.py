import subprocess

from pytest_mock import MockerFixture

from sysbar.services.uninstall.command_query import CommandPackageQuery


def _completed(returncode: int, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def test_snap_name_extracts_package_from_snap_path() -> None:
    assert CommandPackageQuery().snap_name("/snap/foo/bar") == "foo"


def test_snap_name_non_snap_path_returns_none() -> None:
    assert CommandPackageQuery().snap_name("/usr/bin/foo") is None


def test_snap_name_bare_prefix_returns_none() -> None:
    assert CommandPackageQuery().snap_name("/snap/") is None


def test_snap_name_package_without_trailing_path_returns_name() -> None:
    assert CommandPackageQuery().snap_name("/snap/firefox") == "firefox"


def test_owning_apt_package_parses_dpkg_output(mocker: MockerFixture) -> None:
    run = mocker.patch(
        "sysbar.services.uninstall.command_query.subprocess.run",
        return_value=_completed(0, stdout="gedit: /usr/bin/gedit\n"),
    )
    assert CommandPackageQuery().owning_apt_package("/usr/bin/gedit") == "gedit"
    run.assert_called_once()
    assert run.call_args.args[0] == ["dpkg", "-S", "/usr/bin/gedit"]


def test_owning_apt_package_takes_first_of_multiple_packages(mocker: MockerFixture) -> None:
    mocker.patch(
        "sysbar.services.uninstall.command_query.subprocess.run",
        return_value=_completed(0, stdout="pkg-a, pkg-b: /usr/bin/x\n"),
    )
    assert CommandPackageQuery().owning_apt_package("/usr/bin/x") == "pkg-a"


def test_owning_apt_package_dpkg_failure_returns_none(mocker: MockerFixture) -> None:
    mocker.patch(
        "sysbar.services.uninstall.command_query.subprocess.run",
        return_value=_completed(1),
    )
    assert CommandPackageQuery().owning_apt_package("/usr/bin/gedit") is None


def test_flatpak_app_id_none_input_returns_none(mocker: MockerFixture) -> None:
    run = mocker.patch("sysbar.services.uninstall.command_query.subprocess.run")
    assert CommandPackageQuery().flatpak_app_id(None) is None
    run.assert_not_called()


def test_flatpak_app_id_empty_string_returns_none(mocker: MockerFixture) -> None:
    run = mocker.patch("sysbar.services.uninstall.command_query.subprocess.run")
    assert CommandPackageQuery().flatpak_app_id("") is None
    run.assert_not_called()


def test_flatpak_app_id_installed_returns_app_id(mocker: MockerFixture) -> None:
    run = mocker.patch(
        "sysbar.services.uninstall.command_query.subprocess.run",
        return_value=_completed(0, stdout="Firefox\n"),
    )
    assert CommandPackageQuery().flatpak_app_id("org.mozilla.firefox") == "org.mozilla.firefox"
    assert run.call_args.args[0] == ["flatpak", "info", "org.mozilla.firefox"]


def test_flatpak_app_id_not_installed_returns_none(mocker: MockerFixture) -> None:
    mocker.patch(
        "sysbar.services.uninstall.command_query.subprocess.run",
        return_value=_completed(1),
    )
    assert CommandPackageQuery().flatpak_app_id("org.mozilla.firefox") is None


def test_run_returncode_zero_returns_stdout(mocker: MockerFixture) -> None:
    mocker.patch(
        "sysbar.services.uninstall.command_query.subprocess.run",
        return_value=_completed(0, stdout="payload\n"),
    )
    assert CommandPackageQuery()._run(["dpkg", "-S", "/x"]) == "payload\n"


def test_run_nonzero_returncode_returns_none(mocker: MockerFixture) -> None:
    mocker.patch(
        "sysbar.services.uninstall.command_query.subprocess.run",
        return_value=_completed(2, stdout="ignored"),
    )
    assert CommandPackageQuery()._run(["dpkg", "-S", "/x"]) is None


def test_run_file_not_found_returns_none(mocker: MockerFixture) -> None:
    mocker.patch(
        "sysbar.services.uninstall.command_query.subprocess.run",
        side_effect=FileNotFoundError,
    )
    assert CommandPackageQuery()._run(["missing-tool"]) is None


def test_run_timeout_returns_none(mocker: MockerFixture) -> None:
    mocker.patch(
        "sysbar.services.uninstall.command_query.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="dpkg", timeout=5),
    )
    assert CommandPackageQuery()._run(["dpkg", "-S", "/x"]) is None
