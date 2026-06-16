from pathlib import Path

from sysbar.services.autostart import AutostartManager


def test_disabled_by_default(tmp_path: Path) -> None:
    manager = AutostartManager(autostart_dir=tmp_path / "autostart")
    assert manager.is_enabled() is False


def test_enable_creates_desktop_file(tmp_path: Path) -> None:
    manager = AutostartManager(autostart_dir=tmp_path / "autostart")
    manager.enable()
    assert manager.is_enabled() is True
    content = (tmp_path / "autostart" / "it.linkalab.Sysbar.desktop").read_text()
    assert "Exec=sysbar" in content
    assert "X-GNOME-Autostart-enabled=true" in content


def test_disable_removes_file(tmp_path: Path) -> None:
    manager = AutostartManager(autostart_dir=tmp_path / "autostart")
    manager.enable()
    manager.disable()
    assert manager.is_enabled() is False


def test_disable_is_idempotent(tmp_path: Path) -> None:
    manager = AutostartManager(autostart_dir=tmp_path / "autostart")
    manager.disable()
    assert manager.is_enabled() is False


def test_set_enabled_toggles(tmp_path: Path) -> None:
    manager = AutostartManager(autostart_dir=tmp_path / "autostart")
    manager.set_enabled(True)
    assert manager.is_enabled() is True
    manager.set_enabled(False)
    assert manager.is_enabled() is False
