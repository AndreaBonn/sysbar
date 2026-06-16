from pathlib import Path

from sysbar.services.uninstall.leftover_scanner import directory_size, scan_leftovers
from sysbar.services.uninstall.models import LeftoverCategory


def _write(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def test_directory_size_sums_files(tmp_path: Path) -> None:
    _write(tmp_path / "a.txt", 100)
    _write(tmp_path / "sub" / "b.txt", 50)
    assert directory_size(tmp_path) == 150


def test_scan_finds_xdg_residue(tmp_path: Path) -> None:
    _write(tmp_path / ".config" / "foo" / "settings.ini", 10)
    _write(tmp_path / ".cache" / "foo" / "blob", 20)
    _write(tmp_path / ".local" / "share" / "foo" / "data", 30)
    leftovers = scan_leftovers("foo", None, tmp_path)
    categories = {leftover.category for leftover in leftovers}
    assert categories == {
        LeftoverCategory.CONFIG,
        LeftoverCategory.CACHE,
        LeftoverCategory.DATA,
    }


def test_scan_reports_sizes(tmp_path: Path) -> None:
    _write(tmp_path / ".config" / "foo" / "settings.ini", 42)
    leftover = scan_leftovers("foo", None, tmp_path)[0]
    assert leftover.size_bytes == 42


def test_scan_finds_flatpak_data_and_desktop_entry(tmp_path: Path) -> None:
    _write(tmp_path / ".var" / "app" / "org.foo" / "config" / "x", 5)
    _write(tmp_path / ".local" / "share" / "applications" / "org.foo.desktop", 7)
    leftovers = scan_leftovers("Foo", "org.foo", tmp_path)
    categories = {leftover.category for leftover in leftovers}
    assert LeftoverCategory.FLATPAK_DATA in categories
    assert LeftoverCategory.DESKTOP_ENTRY in categories


def test_scan_no_residue_returns_empty(tmp_path: Path) -> None:
    assert scan_leftovers("nothing", None, tmp_path) == []
