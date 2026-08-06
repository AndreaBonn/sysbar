"""Construction smoke tests for every Sysbar window.

Each test builds a window and asserts it materialised. The goal is to fail fast
on a broken widget tree, not to drive interactions; behaviour lives in the
service-level tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sysbar.core.capabilities import Capabilities
from sysbar.core.config import Config
from sysbar.services.audio.models import AudioDevice
from sysbar.services.autostart import AutostartManager
from sysbar.services.scenes.models import Scene
from sysbar.services.scenes.triggers import TriggerRule
from sysbar.services.shelf.shelf_service import ShelfService
from sysbar.services.uninstall.app_uninstaller import AppUninstaller
from sysbar.services.uninstall.models import PackageManager

pytestmark = pytest.mark.ui


class _FakePackageQuery:
    """Minimal :class:`PackageQuery` that performs no I/O."""

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


def test_panel_window_builds(gtk: object) -> None:
    from sysbar.ui.panel.panel_window import PanelWindow

    window = PanelWindow()
    assert window.get_title() == "Sysbar"
    window.destroy()


def test_panel_window_sparklines_update(gtk: object) -> None:
    from sysbar.services.system_monitor.history import MetricHistory
    from sysbar.services.system_monitor.snapshot import SystemSnapshot
    from sysbar.ui.panel.panel_window import PanelWindow

    window = PanelWindow()
    window.set_graph_metrics(frozenset({"cpu"}))
    history = MetricHistory()
    history.record(SystemSnapshot(cpu_percent=10.0))
    history.record(SystemSnapshot(cpu_percent=20.0))
    window.update_history(history)
    window.destroy()


def test_panel_window_net_processes_update(gtk: object) -> None:
    from sysbar.services.system_monitor.net_per_process import ProcNetRate
    from sysbar.ui.panel.panel_window import PanelWindow

    window = PanelWindow()
    window.update_net_processes([ProcNetRate(pid=1, name="firefox", rx_rate=2048.0, tx_rate=512.0)])
    window.destroy()


def test_device_section_binds_and_populates(gtk: object) -> None:
    from sysbar.services.audio.device_switcher import DeviceSwitcher
    from sysbar.services.audio.models import AudioDevice, SinkInput
    from sysbar.ui.panel.device_section import DeviceSection

    class _Backend:
        def list_sinks(self) -> list[AudioDevice]:
            return [AudioDevice(0, "spk", "Speakers", "sink", True)]

        def list_sources(self) -> list[AudioDevice]:
            return [AudioDevice(1, "mic", "Microphone", "source", True)]

        def list_sink_inputs(self) -> list[SinkInput]:
            return []

        def set_default_sink(self, name: str) -> None: ...
        def set_default_source(self, name: str) -> None: ...
        def move_sink_input(self, input_index: int, sink_index: int) -> None: ...

    section = DeviceSection()
    switcher = DeviceSwitcher(_Backend())
    section.bind(switcher)
    switcher.refresh()
    assert section.get_visible()


def test_clipboard_window_builds(gtk: object, tmp_path: Path) -> None:
    from sysbar.services.clipboard.service import ClipboardService
    from sysbar.ui.clipboard.clipboard_window import ClipboardWindow

    service = ClipboardService(tmp_path / "clipboard")
    service.capture("hello")
    window = ClipboardWindow(service, on_copy=lambda _text: None)
    assert window.get_title()
    window.destroy()


def test_settings_window_builds(gtk: object, compiled_schema: str) -> None:
    from sysbar.ui.settings.settings_window import SettingsWindow

    window = SettingsWindow(Config(), AutostartManager())
    assert window.get_title()
    window.destroy()


def test_shelf_window_builds(gtk: object, tmp_path: Path) -> None:
    from sysbar.ui.shelf.shelf_window import ShelfWindow

    window = ShelfWindow(ShelfService(tmp_path))
    assert window.get_title()
    window.destroy()


def test_onboarding_window_builds(gtk: object) -> None:
    from sysbar.ui.onboarding.onboarding_window import OnboardingWindow

    window = OnboardingWindow(Capabilities(), on_finish=lambda: None)
    assert window.get_title() is not None
    window.destroy()


def test_uninstaller_window_builds(gtk: object) -> None:
    from sysbar.ui.uninstall.uninstaller_window import UninstallerWindow

    uninstaller = AppUninstaller(
        home=Path("/tmp"),
        trash=_FakeTrash(),
        remover=_FakeRemover(),
        polkit_available=False,
    )
    window = UninstallerWindow(uninstaller, _FakePackageQuery())
    assert window.get_title()
    window.destroy()


def test_palette_window_builds(gtk: object) -> None:
    from sysbar.ui.palette.palette_window import PaletteWindow

    window = PaletteWindow(lambda _query: [])

    assert window.get_title()
    window.destroy()


def test_palette_window_lists_the_entries_it_is_given(gtk: object) -> None:
    from sysbar.services.palette.models import EntryKind, PaletteEntry, Runnable
    from sysbar.ui.palette.palette_window import PaletteWindow

    entry = PaletteEntry(
        id="open-panel",
        title="Open the panel",
        kind=EntryKind.COMMAND,
        activation=Runnable(invoke=lambda: None),
    )
    window = PaletteWindow(lambda _query: [entry])

    assert window._list.get_row_at_index(0) is not None
    window.destroy()


def test_palette_window_shows_the_empty_state_without_matches(gtk: object) -> None:
    from sysbar.ui.palette.palette_window import PaletteWindow

    window = PaletteWindow(lambda _query: [])

    assert window._stack.get_visible_child_name() == "empty"
    window.destroy()


class _FakeSceneController:
    def __init__(self) -> None:
        from sysbar.services.scenes.models import PRESET_SCENES

        self.scenes = list(PRESET_SCENES)
        self.saved: list[Scene] = []
        self.deleted: list[str] = []
        self.saved_triggers: list[TriggerRule | None] = []

    def save(self, scene: Scene) -> None:
        self.saved.append(scene)

    def delete(self, scene_id: str) -> bool:
        self.deleted.append(scene_id)
        return True

    def outputs(self) -> list[AudioDevice]:
        return []

    def trigger_for(self, scene_id: str) -> TriggerRule | None:
        return None

    def save_trigger(self, rule: TriggerRule | None, scene_id: str) -> None:
        self.saved_triggers.append(rule)


def test_scenes_window_builds(gtk: object) -> None:
    from sysbar.ui.scenes.scenes_window import ScenesWindow

    window = ScenesWindow(_FakeSceneController())

    assert window.get_title()
    window.destroy()


def test_scenes_window_lists_every_scene(gtk: object) -> None:
    from sysbar.services.scenes.models import PRESET_SCENES
    from sysbar.ui.scenes.scenes_window import ScenesWindow

    window = ScenesWindow(_FakeSceneController())

    assert len(window._rows) == len(PRESET_SCENES)
    window.destroy()


def test_scenes_window_opens_the_editor_for_a_new_scene(gtk: object) -> None:
    from sysbar.ui.scenes.scenes_window import ScenesWindow

    window = ScenesWindow(_FakeSceneController())

    window._edit(None)

    assert window._stack.get_visible_child_name() == "edit"
    window.destroy()


def test_editing_a_preset_saves_it_without_losing_actions(gtk: object) -> None:
    from sysbar.services.scenes.models import PRESET_SCENES
    from sysbar.ui.scenes.scenes_window import ScenesWindow

    controller = _FakeSceneController()
    window = ScenesWindow(controller)
    preset = PRESET_SCENES[0]

    window._edit(preset)
    window._editor._save()

    saved = controller.saved[0]
    assert set(saved.actions) == set(preset.actions)
    window.destroy()
