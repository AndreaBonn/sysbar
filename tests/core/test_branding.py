"""Behavioural tests for app-icon search-path registration."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from sysbar.core import branding
from sysbar.core.constants import APP_ICON_NAME


def _install_fake_gtk(monkeypatch: pytest.MonkeyPatch, icon_theme: object) -> None:
    """Swap the lazily-imported ``gi`` for a stub exposing *icon_theme* as ``Gtk.IconTheme``.

    The branding helpers import ``gi`` inside the function body, so replacing the
    entries in ``sys.modules`` lets the GTK call paths run without a real display.
    Only the GTK dependency is faked; the function under test runs unchanged.
    """
    fake_gi = types.SimpleNamespace(require_version=lambda *args, **kwargs: None)
    fake_repository = types.SimpleNamespace(Gtk=types.SimpleNamespace(IconTheme=icon_theme))
    monkeypatch.setitem(sys.modules, "gi", fake_gi)
    monkeypatch.setitem(sys.modules, "gi.repository", fake_repository)


def test_app_icons_dir_returns_path_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    icons = tmp_path / "icons"
    icons.mkdir()
    monkeypatch.setattr(branding, "_SOURCE_ICONS_DIR", icons)

    assert branding.app_icons_dir() == icons


def test_app_icons_dir_none_when_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(branding, "_SOURCE_ICONS_DIR", tmp_path / "missing")

    assert branding.app_icons_dir() is None


def test_register_app_icons_returns_false_without_display(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    icons = tmp_path / "icons"
    icons.mkdir()
    monkeypatch.setattr(branding, "_SOURCE_ICONS_DIR", icons)

    assert branding.register_app_icons(None) is False


def test_register_app_icons_returns_false_when_no_source_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(branding, "_SOURCE_ICONS_DIR", tmp_path / "missing")

    # A truthy sentinel stands in for a display: the absent icons dir must
    # short-circuit before any GTK call, so the sentinel is never touched.
    assert branding.register_app_icons(object()) is False


def test_has_app_icon_false_without_display() -> None:
    assert branding.has_app_icon(None) is False


def test_register_app_icons_adds_source_dir_to_theme_and_returns_true(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    icons = tmp_path / "icons"
    icons.mkdir()
    monkeypatch.setattr(branding, "_SOURCE_ICONS_DIR", icons)

    recorded: dict[str, object] = {}

    class FakeTheme:
        def add_search_path(self, path: str) -> None:
            recorded["path"] = path

    class FakeIconTheme:
        @staticmethod
        def get_for_display(display: object) -> FakeTheme:
            recorded["display"] = display
            return FakeTheme()

    _install_fake_gtk(monkeypatch, FakeIconTheme)
    display = object()

    assert branding.register_app_icons(display) is True
    assert recorded["display"] is display
    assert recorded["path"] == str(icons)


def test_has_app_icon_true_when_theme_knows_the_branded_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTheme:
        def has_icon(self, name: str) -> bool:
            return name == APP_ICON_NAME

    class FakeIconTheme:
        @staticmethod
        def get_for_display(display: object) -> FakeTheme:
            return FakeTheme()

    _install_fake_gtk(monkeypatch, FakeIconTheme)

    assert branding.has_app_icon(object()) is True


def test_has_app_icon_false_when_theme_lacks_the_branded_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTheme:
        def has_icon(self, name: str) -> bool:
            return False

    class FakeIconTheme:
        @staticmethod
        def get_for_display(display: object) -> FakeTheme:
            return FakeTheme()

    _install_fake_gtk(monkeypatch, FakeIconTheme)

    assert branding.has_app_icon(object()) is False
