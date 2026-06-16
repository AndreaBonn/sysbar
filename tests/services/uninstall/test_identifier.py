from sysbar.services.uninstall.identifier import identify
from sysbar.services.uninstall.models import PackageManager


class FakeQuery:
    def __init__(
        self,
        snap: str | None = None,
        apt: str | None = None,
        flatpak: str | None = None,
    ) -> None:
        self._snap = snap
        self._apt = apt
        self._flatpak = flatpak

    def snap_name(self, path: str) -> str | None:
        return self._snap

    def owning_apt_package(self, path: str) -> str | None:
        return self._apt

    def flatpak_app_id(self, app_id: str | None) -> str | None:
        return self._flatpak


def test_identify_apt_package() -> None:
    manager, ref = identify("/usr/bin/gedit", None, FakeQuery(apt="gedit"))
    assert manager is PackageManager.APT
    assert ref == "gedit"


def test_identify_snap_takes_precedence_over_apt() -> None:
    query = FakeQuery(snap="spotify", apt="should-not-win")
    manager, ref = identify("/snap/spotify/current/bin/spotify", None, query)
    assert manager is PackageManager.SNAP
    assert ref == "spotify"


def test_identify_flatpak_by_app_id() -> None:
    manager, ref = identify(None, "org.gimp.GIMP", FakeQuery(flatpak="org.gimp.GIMP"))
    assert manager is PackageManager.FLATPAK
    assert ref == "org.gimp.GIMP"


def test_identify_manual_when_unowned() -> None:
    manager, ref = identify("/opt/app/app", "org.app", FakeQuery())
    assert manager is PackageManager.MANUAL
    assert ref is None
