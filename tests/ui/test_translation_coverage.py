"""Guard against the Italian catalog drifting behind the code.

The catalog ``it/sysbar.po`` is hand-maintained (the build has no ``xgettext``
step), so a newly added ``_("...")`` string stays untranslated until someone
remembers to add it by hand. When that is forgotten the string renders in
English even with the language set to Italian.

This test makes the omission fail CI instead of a user's screen. It installs a
recording translation that captures every message routed through
:func:`sysbar.core.i18n._` (works regardless of which module imported ``_``,
because they all defer to ``i18n._translation.gettext``), then exercises the code
paths that emit user-facing strings: the tray menu across every toggle state,
each window, and the alert engine. Finally it asserts every captured message has
a ``msgid`` in the catalog.

The windows need a display, so the test lives under ``tests/ui`` (skipped without
one; CI runs it under ``xvfb-run``).
"""

from __future__ import annotations

import ast
import gettext
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

import pytest

from sysbar.core import i18n
from sysbar.core.constants import GETTEXT_DOMAIN

pytestmark = pytest.mark.ui

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CATALOG = _PROJECT_ROOT / "data" / "locale" / "it" / "LC_MESSAGES" / f"{GETTEXT_DOMAIN}.po"


class _Destroyable(Protocol):
    def destroy(self) -> None: ...


class _RecordingTranslation(gettext.NullTranslations):
    """A NullTranslations that records every requested message and echoes it."""

    def __init__(self) -> None:
        super().__init__()
        self.seen: set[str] = set()

    def gettext(self, message: str) -> str:
        self.seen.add(message)
        return message


@pytest.fixture
def recorder() -> Iterator[_RecordingTranslation]:
    saved = i18n._translation
    rec = _RecordingTranslation()
    i18n.set_translation(rec)
    try:
        yield rec
    finally:
        i18n.set_translation(saved)


def _catalog_msgids(po: Path) -> set[str]:
    """Return the set of source ``msgid`` strings defined in a ``.po`` file."""
    ids: set[str] = set()
    parts: list[str] = []
    collecting = False
    for line in po.read_text(encoding="utf-8").splitlines():
        if line.startswith("msgid "):
            collecting = True
            parts = [ast.literal_eval(line[len("msgid ") :])]
        elif collecting and line.startswith('"'):
            parts.append(ast.literal_eval(line))
        elif collecting:
            ids.add("".join(parts))
            collecting = False
    if collecting:
        ids.add("".join(parts))
    ids.discard("")
    return ids


def _exercise_tray_menu() -> None:
    """Build the tray tree across the toggle and scene states that vary labels."""
    from sysbar.app.tray.menu_builder import (
        MenuActions,
        QuickToggleState,
        SceneMenuEntry,
        build_menu_items,
    )
    from sysbar.services.scenes.models import PRESET_SCENES

    def _noop() -> None: ...

    def _noop_scene(_scene_id: str) -> None: ...

    actions = MenuActions(
        toggle_keep_awake=_noop,
        toggle_microphone=_noop,
        toggle_dnd=_noop,
        toggle_dark_mode=_noop,
        open_panel=_noop,
        open_shelf=_noop,
        open_clipboard=_noop,
        open_uninstaller=_noop,
        open_settings=_noop,
        open_github=_noop,
        quit=_noop,
        activate_scene=_noop_scene,
        clear_scene=_noop,
    )
    scenes = tuple(
        SceneMenuEntry(id=scene.id, name=scene.name, active=False) for scene in PRESET_SCENES
    )
    for mic_muted in (False, True):
        for dnd_active in (False, True):
            for dark_active in (False, True):
                toggles = QuickToggleState(
                    mic_available=True,
                    mic_muted=mic_muted,
                    mic_in_use=True,
                    dnd_available=True,
                    dnd_active=dnd_active,
                    dark_available=True,
                    dark_active=dark_active,
                )
                build_menu_items(
                    {},
                    keep_awake_on=False,
                    shelf_enabled=True,
                    clipboard_enabled=True,
                    toggles=toggles,
                    actions=actions,
                    scenes=scenes,
                )


def _exercise_alerts() -> None:
    """Drive the alert engine so every alert title and body is materialised."""
    from sysbar.services.system_monitor.alerting import AlertEngine, AlertThresholds
    from sysbar.services.system_monitor.snapshot import SystemSnapshot

    engine = AlertEngine(
        thresholds=lambda: AlertThresholds(
            cpu_percent=80,
            cpu_seconds=0,
            memory_percent=80,
            disk_percent=80,
            temperature_celsius=70,
            battery_percent=20,
        )
    )
    engine.evaluate(
        SystemSnapshot(
            cpu_percent=99.0,
            memory_percent=99.0,
            disk_percent=99.0,
            cpu_temp_celsius=99.0,
            battery_percent=5.0,
            on_battery=True,
        )
    )


def _exercise_windows(tmp_path: Path) -> None:
    """Construct every window so wrapper/combo labels pass through ``_()``."""
    from pathlib import Path as _Path

    from sysbar.core.capabilities import Capabilities
    from sysbar.core.config import Config
    from sysbar.services.autostart import AutostartManager
    from sysbar.services.clipboard.service import ClipboardService
    from sysbar.services.shelf.shelf_service import ShelfService
    from sysbar.services.uninstall.app_uninstaller import AppUninstaller
    from sysbar.services.uninstall.models import PackageManager
    from sysbar.ui.clipboard.clipboard_window import ClipboardWindow
    from sysbar.ui.onboarding.onboarding_window import OnboardingWindow
    from sysbar.ui.panel.panel_window import PanelWindow
    from sysbar.ui.settings.settings_window import SettingsWindow
    from sysbar.ui.shelf.shelf_window import ShelfWindow
    from sysbar.ui.uninstall.uninstaller_window import UninstallerWindow

    class _FakePackageQuery:
        def snap_name(self, path: str) -> str | None:
            return None

        def owning_apt_package(self, path: str) -> str | None:
            return None

        def flatpak_app_id(self, app_id: str | None) -> str | None:
            return None

    class _FakeTrash:
        def trash(self, path: str) -> bool:
            return True

    class _FakeRemover:
        def remove(self, manager: PackageManager, package_ref: str) -> bool:
            return True

    windows: list[_Destroyable] = [
        PanelWindow(),
        ClipboardWindow(ClipboardService(tmp_path / "clipboard"), on_copy=lambda _text: None),
        SettingsWindow(Config(), AutostartManager()),
        ShelfWindow(ShelfService(tmp_path / "shelf")),
        OnboardingWindow(Capabilities(), on_finish=lambda: None),
        UninstallerWindow(
            AppUninstaller(
                home=_Path("/tmp"),
                trash=_FakeTrash(),
                remover=_FakeRemover(),
                polkit_available=False,
            ),
            _FakePackageQuery(),
        ),
    ]
    for window in windows:
        window.destroy()


def test_every_used_string_has_an_italian_catalog_entry(
    gtk: object, compiled_schema: str, recorder: _RecordingTranslation, tmp_path: Path
) -> None:
    _exercise_tray_menu()
    _exercise_alerts()
    _exercise_windows(tmp_path)

    catalog = _catalog_msgids(_CATALOG)
    missing = sorted(message for message in recorder.seen if message and message not in catalog)

    assert not missing, (
        "Strings reach _() but have no msgid in it/sysbar.po (they render in "
        "English under Italian). Add them to the catalog:\n  " + "\n  ".join(missing)
    )
