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
        open_palette=_noop,
        open_scenes=_noop,
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


def _exercise_device_rows() -> None:
    """Render a peripheral row per device kind so every type name reaches _()."""
    from sysbar.app.tray_renderer import render_device_rows
    from sysbar.core.constants import (
        UPOWER_TYPE_GAMING_INPUT,
        UPOWER_TYPE_HEADPHONES,
        UPOWER_TYPE_HEADSET,
        UPOWER_TYPE_KEYBOARD,
        UPOWER_TYPE_MOUSE,
        UPOWER_TYPE_OTHER_AUDIO,
        UPOWER_TYPE_PEN,
        UPOWER_TYPE_PHONE,
        UPOWER_TYPE_SPEAKERS,
        UPOWER_TYPE_TABLET,
        UPOWER_TYPE_TOUCHPAD,
        UPOWER_TYPE_WEARABLE,
    )
    from sysbar.services.system_monitor.models import PeripheralBattery
    from sysbar.services.system_monitor.snapshot import SystemSnapshot

    kinds = (
        UPOWER_TYPE_MOUSE,
        UPOWER_TYPE_KEYBOARD,
        UPOWER_TYPE_PHONE,
        UPOWER_TYPE_TABLET,
        UPOWER_TYPE_GAMING_INPUT,
        UPOWER_TYPE_PEN,
        UPOWER_TYPE_TOUCHPAD,
        UPOWER_TYPE_HEADSET,
        UPOWER_TYPE_SPEAKERS,
        UPOWER_TYPE_HEADPHONES,
        UPOWER_TYPE_OTHER_AUDIO,
        UPOWER_TYPE_WEARABLE,
        0,  # unknown -> generic "Device" fallback
    )
    for kind in kinds:
        snap = SystemSnapshot(
            peripherals=(PeripheralBattery(model="", kind=kind, percent=50.0, charging=False),)
        )
        render_device_rows(snap)


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
    from gi.repository import Gio

    from sysbar.app.whats_new import NOTES
    from sysbar.core.capabilities import Capabilities
    from sysbar.core.config import Config
    from sysbar.services.audio.models import AudioDevice
    from sysbar.services.autostart import AutostartManager
    from sysbar.services.clipboard.service import ClipboardService
    from sysbar.services.scenes.models import PRESET_SCENES, Scene
    from sysbar.services.scenes.triggers import TriggerRule
    from sysbar.services.shelf.shelf_service import ShelfService
    from sysbar.services.uninstall.app_uninstaller import AppUninstaller
    from sysbar.services.uninstall.models import PackageManager
    from sysbar.ui.clipboard.clipboard_window import ClipboardWindow
    from sysbar.ui.onboarding.onboarding_window import OnboardingWindow
    from sysbar.ui.onboarding.whats_new_window import WhatsNewWindow
    from sysbar.ui.palette.palette_window import PaletteWindow
    from sysbar.ui.panel.mixer_section import MixerSection
    from sysbar.ui.panel.panel_window import PanelWindow
    from sysbar.ui.scenes.scenes_window import ScenesWindow
    from sysbar.ui.settings.settings_window import SettingsWindow
    from sysbar.ui.shelf.shelf_window import ShelfWindow
    from sysbar.ui.uninstall.uninstaller_window import UninstallerWindow

    class _FakeSceneController:
        def __init__(self) -> None:
            self.scenes = list(PRESET_SCENES)
            self.active_id = PRESET_SCENES[0].id

        def activate(self, scene_id: str) -> None:
            self.active_id = scene_id

        def save(self, scene: Scene) -> None: ...

        def delete(self, scene_id: str) -> bool:
            return False

        def outputs(self) -> list[AudioDevice]:
            return []

        def trigger_for(self, scene_id: str) -> TriggerRule | None:
            return None

        def save_trigger(self, rule: TriggerRule | None, scene_id: str) -> None: ...

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

    shelf_service = ShelfService(tmp_path / "shelf")
    shelf_service.add_file(str(tmp_path / "dropped.txt"))  # render a tile so its tooltip emits _()

    windows: list[_Destroyable] = [
        WhatsNewWindow(NOTES, on_seen=lambda: None),
        PanelWindow(),
        PaletteWindow(lambda _query: []),
        ScenesWindow(_FakeSceneController()),
        ClipboardWindow(ClipboardService(tmp_path / "clipboard"), on_copy=lambda _text: None),
        SettingsWindow(
            Config(backend=Gio.memory_settings_backend_new()),
            AutostartManager(autostart_dir=tmp_path / "autostart"),
            on_show_onboarding=lambda: None,
        ),
        SettingsWindow(
            Config(backend=Gio.memory_settings_backend_new()),
            AutostartManager(autostart_dir=tmp_path / "autostart"),
            on_show_onboarding=lambda: None,
            shortcuts_available=False,
        ),
        ShelfWindow(shelf_service),
        OnboardingWindow(
            Capabilities(),
            config=Config(backend=Gio.memory_settings_backend_new()),
            autostart=AutostartManager(autostart_dir=tmp_path / "autostart"),
            on_finish=lambda: None,
        ),
        UninstallerWindow(
            AppUninstaller(
                home=tmp_path,
                trash=_FakeTrash(),
                remover=_FakeRemover(),
                polkit_available=False,
            ),
            _FakePackageQuery(),
        ),
    ]
    for window in windows:
        window.destroy()
    MixerSection().set_unavailable()  # a title set outside any window constructor


def _exercise_panel_and_palette_content() -> None:
    """Call every string-emitting branch of the panel, palette and clipboard modules."""
    from sysbar.app.clipboard_content import empty_state as clipboard_empty
    from sysbar.app.clipboard_content import pin_presentation
    from sysbar.app.palette_content import empty_state as palette_empty
    from sysbar.app.palette_content import section_title
    from sysbar.app.panel_rows import process_row_text
    from sysbar.services.palette.models import EntryKind
    from sysbar.services.system_monitor.processes import ProcessUsage

    for name in ("", "firefox"):
        process_row_text(ProcessUsage(pid=1, name=name, cpu_percent=1.0, memory_bytes=1024))
    previous: str | None = None
    for kind in EntryKind:
        section_title(kind.value, previous)
    for query in ("", "mic"):
        palette_empty(query)
        clipboard_empty(query)
    for pinned in (False, True):
        pin_presentation(pinned)


def _exercise_scene_content() -> None:
    """Translate the scene tables the way the editor does, and every summary phrase."""
    from sysbar.app.device_choices import scene_output_choices
    from sysbar.app.scenes_content import REMOVAL_PRESENTATIONS, TOGGLE_CHOICES, TRIGGER_CHOICES
    from sysbar.core.i18n import _
    from sysbar.services.scenes.actions import (
        SetOutputDevice,
        SetSetting,
        SetToggle,
        SystemToggle,
    )
    from sysbar.services.scenes.apply import ActionOutcome, Status
    from sysbar.services.scenes.constants import SCENE_WRITABLE_KEYS
    from sysbar.services.scenes.models import Scene
    from sysbar.services.scenes.summary import describe_scene, partial_note, trigger_announcement

    for _choice, label in (*TRIGGER_CHOICES, *TOGGLE_CHOICES):
        _(label)
    for _icon, tooltip in REMOVAL_PRESENTATIONS.values():
        _(tooltip)
    scene_output_choices(devices=[], selected_name="unplugged-sink")

    toggles = tuple(SetToggle(toggle, value) for toggle in SystemToggle for value in (True, False))
    setting = SetSetting(key=sorted(SCENE_WRITABLE_KEYS)[0], value=True)
    full = Scene(id="x", name="X", actions=(*toggles, SetOutputDevice("sink"), setting))
    describe_scene(full)
    describe_scene(full, device_name=lambda _name: "Speakers")
    describe_scene(Scene(id="y", name="Y"))

    applied = ActionOutcome(action=toggles[0], status=Status.APPLIED)
    failed = ActionOutcome(action=toggles[1], status=Status.FAILED)
    partial_note([applied, failed], "X")
    trigger_announcement("X", [applied, failed])
    trigger_announcement("X", [applied])


def _exercise_uninstall_and_settings_content() -> None:
    """Hit each status, subtitle and message branch of the uninstaller and settings copy."""
    from sysbar.app.settings_content import (
        ALERTS,
        PLACEMENT_OPTIONS,
        SHORTCUTS,
        alert_subtitle,
        tray_preview_text,
    )
    from sysbar.app.uninstall_content import (
        category_label,
        package_subtitle,
        removal_message,
        removal_summary,
    )
    from sysbar.core.i18n import _
    from sysbar.services.uninstall.models import LeftoverCategory, PackageManager, RemovalResult

    for category in LeftoverCategory:
        category_label(category)
    removal_summary(chosen=False, count=0, size_bytes=0)
    removal_summary(chosen=True, count=0, size_bytes=0)
    removal_summary(chosen=True, count=3, size_bytes=2048)
    package_subtitle(PackageManager.APT, "gimp", removable=True)
    package_subtitle(PackageManager.MANUAL, None, removable=False)
    removal_message(RemovalResult(freed_bytes=2048, failed=[]))
    removal_message(RemovalResult(freed_bytes=2048, failed=["a"]))

    for _key, label in PLACEMENT_OPTIONS:
        _(label)
    for spec in ALERTS:
        _(spec.title)
        for value in (0, 50):
            alert_subtitle(spec, value, cpu_seconds=30)
    for shortcut in SHORTCUTS:
        _(shortcut.title)
    for preview in (None, "", "CPU 3%"):
        tray_preview_text(preview)


def _exercise_content() -> None:
    """Exercise the pure modules that now own the user-facing strings.

    These strings no longer pass through a window the gate builds, so every branch
    that emits one is called here directly, with the same ``_()`` wrapping the UI
    applies to the label tables.
    """
    _exercise_panel_and_palette_content()
    _exercise_scene_content()
    _exercise_uninstall_and_settings_content()


def test_every_used_string_has_an_italian_catalog_entry(
    gtk: object, compiled_schema: str, recorder: _RecordingTranslation, tmp_path: Path
) -> None:
    _exercise_tray_menu()
    _exercise_device_rows()
    _exercise_alerts()
    _exercise_content()
    _exercise_windows(tmp_path)

    assert {"Welcome to Sysbar", "Start at login"} <= recorder.seen, "the exercise recorded nothing"
    catalog = _catalog_msgids(_CATALOG)
    missing = sorted(message for message in recorder.seen if message and message not in catalog)

    assert not missing, (
        "Strings reach _() but have no msgid in it/sysbar.po (they render in "
        "English under Italian). Add them to the catalog:\n  " + "\n  ".join(missing)
    )
