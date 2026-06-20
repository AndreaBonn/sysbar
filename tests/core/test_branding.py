"""Behavioural tests for app-icon search-path registration."""

from __future__ import annotations

from pathlib import Path

import pytest

from sysbar.core import branding


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
