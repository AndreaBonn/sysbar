from importlib.metadata import PackageNotFoundError, version

from pytest_mock import MockerFixture

import sysbar


def test_version_matches_installed_package_metadata() -> None:
    assert sysbar.__version__ == version("sysbar")


def test_resolve_version_falls_back_when_package_missing(mocker: MockerFixture) -> None:
    mocker.patch("sysbar.version", side_effect=PackageNotFoundError("sysbar"))

    assert sysbar._resolve_version() == sysbar._FALLBACK_VERSION
