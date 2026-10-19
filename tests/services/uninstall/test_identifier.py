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


def test_target_from_app_strips_only_desktop_suffix() -> None:
    from sysbar.services.uninstall.identifier import target_from_app
    from sysbar.services.uninstall.models import AppTarget

    for desktop_id, app_id in [
        ("org.gnome.Foo.desktop", "org.gnome.Foo"),
        ("org.desktop.Foo", "org.desktop.Foo"),
        ("", None),
        (None, None),
    ]:
        assert target_from_app(
            name="Foo", desktop_id=desktop_id, exec_path=None, query=FakeQuery()
        ) == AppTarget(name="Foo", app_id=app_id, exec_path=None, manager=PackageManager.MANUAL)


def test_target_from_app_without_executable_identifies_flatpak() -> None:
    from sysbar.services.uninstall.identifier import target_from_app

    target = target_from_app(
        name="Foo",
        desktop_id="org.gnome.Foo.desktop",
        exec_path=None,
        query=FakeQuery(flatpak="org.gnome.Foo"),
    )
    assert target.exec_path is None
    assert target.manager is PackageManager.FLATPAK
    assert target.package_ref == "org.gnome.Foo"


def test_target_from_app_identifies_apt_and_snap_executables() -> None:
    from sysbar.services.uninstall.identifier import target_from_app

    for path, query, manager, ref in [
        ("/usr/bin/gedit", FakeQuery(apt="gedit"), PackageManager.APT, "gedit"),
        (
            "/snap/spotify/current/bin/spotify",
            FakeQuery(snap="spotify"),
            PackageManager.SNAP,
            "spotify",
        ),
    ]:
        target = target_from_app(name="Editor", desktop_id=None, exec_path=path, query=query)
        assert target.exec_path == path
        assert target.manager is manager
        assert target.package_ref == ref
