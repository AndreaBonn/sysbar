from pathlib import Path

from sysbar.services.uninstall.app_uninstaller import AppUninstaller
from sysbar.services.uninstall.models import (
    AppTarget,
    Leftover,
    LeftoverCategory,
    PackageManager,
    Phase,
)


class FakeTrash:
    def __init__(self, succeed: bool = True) -> None:
        self.trashed: list[str] = []
        self._succeed = succeed

    def trash(self, path: str) -> bool:
        self.trashed.append(path)
        return self._succeed


class FakeRemover:
    def __init__(self, succeed: bool = True) -> None:
        self.removed: list[tuple[PackageManager, str]] = []
        self._succeed = succeed

    def remove(self, manager: PackageManager, package_ref: str) -> bool:
        self.removed.append((manager, package_ref))
        return self._succeed


def _leftover(path: str, size: int) -> Leftover:
    return Leftover(category=LeftoverCategory.CONFIG, path=path, size_bytes=size)


def _uninstaller(
    tmp_path: Path,
    trash: FakeTrash | None = None,
    remover: FakeRemover | None = None,
    polkit: bool = True,
) -> tuple[AppUninstaller, FakeTrash, FakeRemover]:
    trash = trash or FakeTrash()
    remover = remover or FakeRemover()
    return AppUninstaller(tmp_path, trash, remover, polkit_available=polkit), trash, remover


def test_scan_transitions_to_results(tmp_path: Path) -> None:
    (tmp_path / ".config" / "foo").mkdir(parents=True)
    (tmp_path / ".config" / "foo" / "x").write_bytes(b"data")
    uninstaller, _trash, _remover = _uninstaller(tmp_path)
    target = AppTarget(name="foo", app_id=None, exec_path=None, manager=PackageManager.MANUAL)
    leftovers = uninstaller.scan(target)
    assert uninstaller.phase is Phase.RESULTS
    assert len(leftovers) == 1


def test_remove_trashes_leftovers_and_sums_freed(tmp_path: Path) -> None:
    uninstaller, trash, _remover = _uninstaller(tmp_path)
    target = AppTarget(name="foo", app_id=None, exec_path=None, manager=PackageManager.MANUAL)
    uninstaller.scan(target)
    result = uninstaller.remove([_leftover("/a", 100), _leftover("/b", 50)], remove_package=False)
    assert trash.trashed == ["/a", "/b"]
    assert result.freed_bytes == 150
    assert result.failed == []
    assert uninstaller.phase is Phase.DONE


def test_failed_trash_is_reported_and_not_counted(tmp_path: Path) -> None:
    uninstaller, _trash, _remover = _uninstaller(tmp_path, trash=FakeTrash(succeed=False))
    uninstaller.scan(AppTarget("foo", None, None, PackageManager.MANUAL))
    result = uninstaller.remove([_leftover("/a", 100)], remove_package=False)
    assert result.freed_bytes == 0
    assert result.failed == ["/a"]


def test_package_removed_when_requested_and_allowed(tmp_path: Path) -> None:
    uninstaller, _trash, remover = _uninstaller(tmp_path)
    target = AppTarget("gedit", None, "/usr/bin/gedit", PackageManager.APT, package_ref="gedit")
    uninstaller.scan(target)
    uninstaller.remove([], remove_package=True)
    assert remover.removed == [(PackageManager.APT, "gedit")]


def test_package_not_removed_without_polkit(tmp_path: Path) -> None:
    uninstaller, _trash, remover = _uninstaller(tmp_path, polkit=False)
    target = AppTarget("gedit", None, "/usr/bin/gedit", PackageManager.APT, package_ref="gedit")
    uninstaller.scan(target)
    uninstaller.remove([], remove_package=True)
    assert remover.removed == []


def test_manual_install_package_never_removed(tmp_path: Path) -> None:
    uninstaller, _trash, remover = _uninstaller(tmp_path)
    target = AppTarget("app", None, "/opt/app", PackageManager.MANUAL)
    uninstaller.scan(target)
    uninstaller.remove([], remove_package=True)
    assert remover.removed == []
