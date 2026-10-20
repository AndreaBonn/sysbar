"""Construction smoke tests for every Sysbar window.

Each test builds a window and asserts it materialised. The goal is to fail fast
on a broken widget tree, not to drive interactions; behaviour lives in the
service-level tests.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from sysbar.core.capabilities import Capabilities
from sysbar.core.config import Config
from sysbar.services.audio.models import AudioDevice, SinkInput
from sysbar.services.autostart import AutostartManager
from sysbar.services.scenes.actions import SetOutputDevice, SetToggle, SystemToggle
from sysbar.services.scenes.models import Scene
from sysbar.services.scenes.triggers import BatteryBelow, TriggerRule
from sysbar.services.shelf.shelf_service import ShelfService
from sysbar.services.uninstall.app_uninstaller import AppUninstaller
from sysbar.services.uninstall.models import PackageManager

if TYPE_CHECKING:
    from gi.repository import Gtk

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
    history.record(SystemSnapshot(cpu_percent=10.0, memory_percent=30.0))
    history.record(SystemSnapshot(cpu_percent=20.0, memory_percent=40.0))
    window.update_history(history)

    cpu = window._metrics._sparklines["cpu"]
    assert cpu.get_visible() is True
    assert cpu._values == (10.0, 20.0)
    assert window._metrics._sparklines["memory"].get_visible() is False
    window.destroy()


def test_panel_window_net_processes_update(gtk: object) -> None:
    from sysbar.services.system_monitor.net_per_process import ProcNetRate
    from sysbar.ui.panel.panel_window import PanelWindow

    window = PanelWindow()
    window.update_net_processes([ProcNetRate(pid=1, name="firefox", rx_rate=2048.0, tx_rate=512.0)])

    assert window._net_group.get_visible() is True
    assert [(row.get_title(), row.get_subtitle()) for row in window._net_rows] == [
        ("firefox", "↓2.0 KB/s ↑512 B/s")
    ]
    window.update_net_processes([])
    assert window._net_group.get_visible() is False
    assert window._net_rows == []
    window.destroy()


def test_metrics_section_shows_rows_with_data_and_hides_the_rest(gtk: object) -> None:
    """Every key ``metric_rows`` emits must name a row the section built.

    The values are decided in ``app/panel_rows``; this drives the glue that
    routes them to widgets, which a key drift would break with a KeyError.
    """
    from sysbar.services.system_monitor.snapshot import SystemSnapshot
    from sysbar.ui.panel.metrics_section import MetricsSection

    section = MetricsSection()

    section.update_snapshot(SystemSnapshot(cpu_percent=42.0, power_watts=7.4))

    rows = section._rows
    assert rows["cpu"].row.get_visible() is True
    assert rows["cpu"]._value.get_label() == "42%"
    assert rows["cpu"]._level is not None
    assert rows["cpu"]._level.get_value() == 42.0
    assert rows["power"]._value.get_label() == "7 W"
    assert rows["gpu"].row.get_visible() is False
    assert rows["net_speed"].row.get_visible() is False


def test_device_section_binds_and_populates(gtk: object) -> None:
    from sysbar.services.audio.device_switcher import DeviceSwitcher
    from sysbar.services.audio.models import AudioDevice
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
    _drain_main_loop()
    assert section.get_visible()


def _drain_main_loop() -> None:
    """Run the idle callbacks a refresh schedules (DeviceSection repopulates on idle)."""
    from gi.repository import GLib

    context = GLib.MainContext.default()
    while context.iteration(False):
        pass


class _DeviceBackend:
    def __init__(self) -> None:
        self.outputs = [
            AudioDevice(index=10, name="spk", description="Speakers", kind="sink", is_default=True),
            AudioDevice(index=20, name="hdmi", description="HDMI", kind="sink", is_default=False),
        ]
        self.inputs = [
            AudioDevice(index=30, name="mic", description="Mic", kind="source", is_default=True),
            AudioDevice(index=40, name="usb", description="USB", kind="source", is_default=False),
        ]
        self.switched: list[str] = []

    def list_sinks(self) -> list[AudioDevice]:
        return self.outputs

    def list_sources(self) -> list[AudioDevice]:
        return self.inputs

    def list_sink_inputs(self) -> list[SinkInput]:
        return []

    def set_default_sink(self, name: str) -> None:
        self.switched.append(name)
        self.outputs = [replace(d, is_default=d.name == name) for d in self.outputs]

    def set_default_source(self, name: str) -> None:
        self.switched.append(name)
        self.inputs = [replace(d, is_default=d.name == name) for d in self.inputs]

    def move_sink_input(self, input_index: int, sink_index: int) -> None: ...


def test_device_section_fill_shows_labels_defaults_and_hides_empty_rows(gtk: object) -> None:
    from sysbar.services.audio.device_switcher import DeviceSwitcher
    from sysbar.ui.panel.device_section import DeviceSection

    backend = _DeviceBackend()
    switcher = DeviceSwitcher(backend=backend)
    section = DeviceSection()
    section.bind(switcher=switcher)
    switcher.refresh()
    _drain_main_loop()

    assert section.get_visible() is True
    assert section._output_row.get_visible() is True
    assert section._input_row.get_visible() is True
    assert section._output_row.get_selected_item().get_string() == "Speakers"
    assert section._output_row.get_model().get_string(1) == "HDMI"
    assert section._input_row.get_selected_item().get_string() == "Mic"
    assert backend.switched == []
    section._output_row.set_selected(1)
    _drain_main_loop()
    assert backend.switched == ["hdmi"]
    assert section._output_row.get_selected_item().get_string() == "HDMI"
    backend.outputs = []
    backend.inputs = []
    switcher.refresh()
    _drain_main_loop()
    assert section.get_visible() is False
    assert section._output_row.get_visible() is False
    assert section._input_row.get_visible() is False
    assert section._output_row.get_model().get_n_items() == 0


def test_device_section_input_selection_switches_the_named_device(gtk: object) -> None:
    from sysbar.services.audio.device_switcher import DeviceSwitcher
    from sysbar.ui.panel.device_section import DeviceSection

    backend = _DeviceBackend()
    switcher = DeviceSwitcher(backend=backend)
    section = DeviceSection()
    section.bind(switcher=switcher)
    switcher.refresh()
    _drain_main_loop()

    assert section._input_row.get_model().get_string(1) == "USB"
    assert backend.switched == []
    section._input_row.set_selected(1)
    _drain_main_loop()
    assert backend.switched == ["usb"]
    assert section._input_row.get_selected_item().get_string() == "USB"


def test_clipboard_window_builds(gtk: object, tmp_path: Path) -> None:
    from sysbar.services.clipboard.service import ClipboardService
    from sysbar.ui.clipboard.clipboard_window import ClipboardWindow

    service = ClipboardService(tmp_path / "clipboard")
    service.capture("hello")
    window = ClipboardWindow(service, on_copy=lambda _text: None)
    assert window.get_title()
    window.destroy()


def test_settings_window_builds(gtk: object, compiled_schema: str, tmp_path: Path) -> None:
    from gi.repository import Gio

    from sysbar.ui.settings.settings_window import SettingsWindow

    window = SettingsWindow(
        Config(backend=Gio.memory_settings_backend_new()),
        AutostartManager(autostart_dir=tmp_path),
        on_show_onboarding=lambda: None,
    )
    assert window.get_title()
    window.destroy()


def test_alerts_page_switch_sets_suggested_threshold_and_off_zeroes_it(
    gtk: object, compiled_schema: str
) -> None:
    from gi.repository import Gio

    from sysbar.app.settings_content import ALERTS
    from sysbar.ui.settings.alerts_page import AlertsPage

    spec = ALERTS[-1]
    settings = Gio.Settings.new("io.github.AndreaBonn.Sysbar")
    settings.set_int(spec.key, 0)
    page = AlertsPage(settings)
    row = next(r for s, r in page._rows if s is spec)
    row.set_enable_expansion(True)
    assert settings.get_int(spec.key) == spec.suggested
    row.set_enable_expansion(False)
    assert settings.get_int(spec.key) == 0
    page.disconnect_settings()


def test_shelf_window_builds(gtk: object, tmp_path: Path) -> None:
    from sysbar.ui.shelf.shelf_window import ShelfWindow

    window = ShelfWindow(ShelfService(tmp_path))
    assert window.get_title()
    window.destroy()


def test_onboarding_window_builds(gtk: object, compiled_schema: str, tmp_path: Path) -> None:
    from gi.repository import Gio

    from sysbar.ui.onboarding.onboarding_window import OnboardingWindow

    window = OnboardingWindow(
        Capabilities(),
        config=Config(backend=Gio.memory_settings_backend_new()),
        autostart=AutostartManager(autostart_dir=tmp_path),
        on_finish=lambda: None,
    )
    assert window.get_title() == "Welcome to Sysbar"
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

    row = window._list.get_row_at_index(0)
    assert row.get_title() == "Open the panel"
    assert window._list.get_row_at_index(1) is None
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
        self.active_id = PRESET_SCENES[0].id
        self.saved: list[Scene] = []
        self.deleted: list[str] = []
        self.saved_triggers: list[TriggerRule | None] = []
        self.output_devices: list[AudioDevice] = []

    def activate(self, scene_id: str) -> None:
        self.active_id = scene_id

    def save(self, scene: Scene) -> None:
        self.saved.append(scene)

    def delete(self, scene_id: str) -> bool:
        self.deleted.append(scene_id)
        return True

    def outputs(self) -> list[AudioDevice]:
        return self.output_devices

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


def _scene_icon_buttons(widget: Gtk.Widget) -> list[tuple[str, str | None]]:
    """Read icon buttons through the row's widget tree without a view accessor."""
    from gi.repository import Gtk

    found: list[tuple[str, str | None]] = []
    child = widget.get_first_child()
    while child is not None:
        if isinstance(child, Gtk.Button) and child.get_icon_name():
            found.append((child.get_icon_name(), child.get_tooltip_text()))
        found.extend(_scene_icon_buttons(widget=child))
        child = child.get_next_sibling()
    return found


def _removal_scene_controller() -> _FakeSceneController:
    from sysbar.services.scenes.models import PRESET_SCENES, SceneOrigin

    controller = _FakeSceneController()
    controller.scenes = [
        PRESET_SCENES[0],
        PRESET_SCENES[1].edited(name="My presentation", actions=None),
        Scene(
            id="desk",
            name="Desk",
            origin=SceneOrigin.USER,
            actions=(SetOutputDevice(device="hdmi"),),
        ),
    ]
    controller.output_devices = [
        AudioDevice(index=1, name="hdmi", description="Desk speakers", kind="sink", is_default=True)
    ]
    return controller


def test_scenes_window_removal_buttons_and_output_description(gtk: object) -> None:
    from sysbar.ui.scenes.scenes_window import ScenesWindow

    window = ScenesWindow(controller=_removal_scene_controller())
    try:
        assert [_scene_icon_buttons(widget=row) for row in window._rows] == [
            [("document-edit-symbolic", "Edit")],
            [("document-edit-symbolic", "Edit"), ("edit-undo-symbolic", "Restore the built-in")],
            [("document-edit-symbolic", "Edit"), ("user-trash-symbolic", "Delete")],
        ]
        assert window._rows[2].get_subtitle() == "Audio to Desk speakers"
    finally:
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


def test_scene_editor_keeps_a_disconnected_output_on_save(gtk: object) -> None:
    """Editing a scene whose device is unplugged must not erase that device."""
    from sysbar.ui.scenes.scenes_window import ScenesWindow

    controller = _FakeSceneController()
    controller.output_devices = [
        AudioDevice(index=10, name="speakers", description="Speakers", kind="sink", is_default=True)
    ]
    scene = Scene(id="desk", name="Desk", actions=(SetOutputDevice(device="usb-dac"),))
    window = ScenesWindow(controller=controller)

    window._edit(scene)
    editor = window._editor
    assert editor._device_row.get_selected_item().get_string() == "usb-dac (disconnected)"
    editor._save()

    assert controller.saved[0].actions == (SetOutputDevice(device="usb-dac"),)
    window.destroy()


def test_scene_editor_saves_selected_output_toggle_and_battery_trigger(gtk: object) -> None:
    from sysbar.ui.scenes.scenes_window import ScenesWindow

    controller = _FakeSceneController()
    controller.output_devices = [
        AudioDevice(
            index=10, name="speakers", description="Speakers", kind="sink", is_default=True
        ),
        AudioDevice(index=11, name="hdmi", description="HDMI", kind="sink", is_default=False),
    ]
    window = ScenesWindow(controller=controller)
    window._edit(None)
    editor = window._editor
    assert editor._percent_row.get_visible() is False
    assert editor._restore_row.get_visible() is False
    assert editor._device_row.get_selected_item().get_string() == "Leave unchanged"
    editor._device_row.set_selected(2)
    editor._trigger_row.set_selected(3)
    editor._percent_row.set_value(30)
    editor._restore_row.set_active(True)
    editor._toggle_rows[SystemToggle.KEEP_AWAKE].set_selected(1)
    assert editor._percent_row.get_visible() is True
    assert editor._restore_row.get_visible() is True
    assert editor._trigger_row.get_selected_item().get_string() == "Battery drops below a level"
    assert (
        editor._toggle_rows[SystemToggle.KEEP_AWAKE].get_selected_item().get_string() == "Turn on"
    )
    editor._save()
    _assert_saved_scene_form(controller=controller)
    window.destroy()


def _assert_saved_scene_form(controller: _FakeSceneController) -> None:
    saved = controller.saved[0]
    assert saved.actions == (
        SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=True),
        SetOutputDevice(device="hdmi"),
    )
    assert controller.saved_triggers == [
        TriggerRule(
            id=f"scene:{saved.id}",
            scene_id=saved.id,
            condition=BatteryBelow(percent=30),
            restore_on_exit=True,
        )
    ]


def test_activating_a_scene_from_the_list_marks_it_active(gtk: object) -> None:
    from sysbar.services.scenes.models import PRESET_SCENES
    from sysbar.ui.scenes.scenes_window import ScenesWindow

    controller = _FakeSceneController()
    window = ScenesWindow(controller)
    target = PRESET_SCENES[1]

    window._activate(target.id)

    assert controller.active_id == target.id
    window.destroy()


def test_uninstaller_scans_nothing_until_an_app_is_chosen(gtk: object) -> None:
    from sysbar.services.uninstall.app_uninstaller import AppUninstaller
    from sysbar.ui.uninstall.uninstaller_window import UninstallerWindow

    window = UninstallerWindow(
        AppUninstaller(
            home=Path("/nonexistent"),
            trash=_FakeTrash(),
            remover=_FakeRemover(),
            polkit_available=False,
        ),
        _FakePackageQuery(),
    )

    assert window._target is None
    assert window._remove_button.get_sensitive() is False
    window.destroy()


def test_closing_the_whats_new_window_marks_the_notes_as_seen(gtk: object) -> None:
    from sysbar.app.whats_new import NOTES
    from sysbar.ui.onboarding.whats_new_window import WhatsNewWindow

    seen: list[bool] = []
    window = WhatsNewWindow(NOTES, on_seen=lambda: seen.append(True))
    # close-request only fires for a window that was actually shown.
    window.present()
    window.close()

    assert seen == [True]


def test_palette_window_run_invokes_a_runnable_entry_and_closes(gtk: object) -> None:
    from sysbar.services.palette.models import EntryKind, PaletteEntry, Runnable
    from sysbar.ui.palette.palette_window import PaletteWindow

    calls: list[str] = []
    entry = PaletteEntry(
        id="open-panel",
        title="Open the panel",
        kind=EntryKind.COMMAND,
        activation=Runnable(invoke=lambda: calls.append("ran")),
    )
    window = PaletteWindow(lambda _query: [entry])

    window._run(0)

    assert calls == ["ran"]
    assert window._closing is True
    window.destroy()


def test_palette_window_run_applies_the_fix_of_an_unavailable_entry(gtk: object) -> None:
    from sysbar.services.palette.models import EntryKind, PaletteEntry, Unavailable
    from sysbar.ui.palette.palette_window import PaletteWindow

    fixed: list[str] = []
    entry = PaletteEntry(
        id="mic",
        title="Mute microphone",
        kind=EntryKind.TOGGLE,
        activation=Unavailable(
            reason="Off", fix=lambda: fixed.append("fixed"), fix_label="Turn on"
        ),
    )
    window = PaletteWindow(lambda _query: [entry])

    window._run(0)

    assert fixed == ["fixed"]
    assert window._closing is False
    window.destroy()


def test_palette_window_run_ignores_a_dead_end_entry(gtk: object) -> None:
    from sysbar.services.palette.models import EntryKind, PaletteEntry, Unavailable
    from sysbar.ui.palette.palette_window import PaletteWindow

    entry = PaletteEntry(
        id="mic",
        title="Mute microphone",
        kind=EntryKind.TOGGLE,
        activation=Unavailable(reason="No microphone"),
    )
    window = PaletteWindow(lambda _query: [entry])

    window._run(0)

    assert window._closing is False
    window.destroy()


def test_palette_window_shows_a_section_header_and_the_empty_title(gtk: object) -> None:
    from sysbar.services.palette.models import EntryKind, PaletteEntry, Runnable
    from sysbar.ui.palette.palette_window import PaletteWindow

    entry = PaletteEntry(
        id="open-panel",
        title="Open the panel",
        kind=EntryKind.COMMAND,
        activation=Runnable(invoke=lambda: None),
    )
    window = PaletteWindow(lambda query: [entry] if not query else [])

    header = window._list.get_row_at_index(0).get_header()
    assert header is not None
    assert header.get_label() == "Actions"
    window._entry.set_text("zzz")
    window._refresh()
    assert window._empty.get_title() == "Nothing matches “zzz”"
    window.destroy()


def _tooltips(widget: object) -> list[str]:
    """Collect the tooltip of every descendant widget that has one."""
    found: list[str] = []
    child = widget.get_first_child()  # type: ignore[attr-defined]
    while child is not None:
        tooltip = child.get_tooltip_text()
        if tooltip:
            found.append(tooltip)
        found.extend(_tooltips(child))
        child = child.get_next_sibling()
    return found


def test_clipboard_window_shows_empty_states_and_pin_tooltips(gtk: object, tmp_path: Path) -> None:
    from sysbar.services.clipboard.service import ClipboardService
    from sysbar.ui.clipboard.clipboard_window import ClipboardWindow

    service = ClipboardService(tmp_path / "clipboard")
    window = ClipboardWindow(service, on_copy=lambda _text: None)
    assert window._empty.get_title() == "Nothing copied yet"

    service.capture("hello")
    assert "Pin" in _tooltips(window._rows[0])
    assert "Unpin" not in _tooltips(window._rows[0])
    window._search.set_text("zzz")
    window._rebuild()
    assert window._empty.get_title() == "No entries match"
    window.destroy()


def test_palette_window_header_only_on_the_first_row_of_a_kind(gtk: object) -> None:
    from sysbar.services.palette.models import EntryKind, PaletteEntry, Runnable
    from sysbar.ui.palette.palette_window import PaletteWindow

    entries = [
        PaletteEntry(
            id=f"cmd-{n}",
            title=f"Command {n}",
            kind=EntryKind.COMMAND,
            activation=Runnable(invoke=lambda: None),
        )
        for n in range(2)
    ]
    window = PaletteWindow(lambda _query: entries)

    assert window._list.get_row_at_index(0).get_header() is not None
    assert window._list.get_row_at_index(1).get_header() is None
    window.destroy()


def test_shelf_clear_then_undo_restores_visible_tiles(gtk: object, tmp_path: Path) -> None:
    from gi.repository import Adw

    from sysbar.ui.shelf.shelf_window import ShelfWindow

    service = ShelfService(data_dir=tmp_path / "shelf")
    item = service.add_text(text="Keep this")
    window = ShelfWindow(service=service)
    toasts: list[Adw.Toast] = []
    add_toast = window._toasts.add_toast

    def record(toast: Adw.Toast) -> None:
        toasts.append(toast)
        add_toast(toast)

    window._toasts.add_toast = record
    try:
        assert window._stack.get_visible_child_name() == "tiles"
        window._on_clear(None)
        assert service.items == []
        assert window._stack.get_visible_child_name() == "empty"
        assert window._flow.get_first_child() is None
        toasts[0].emit("button-clicked")
        assert service.items == [item]
        assert window._stack.get_visible_child_name() == "tiles"
        assert window._flow.get_child_at_index(0).get_child().get_first_child() is not None
        assert window._flow.get_child_at_index(1) is None
    finally:
        window.destroy()


def test_shelf_second_clear_can_still_be_undone(gtk: object, tmp_path: Path) -> None:
    """A clear made while the previous toast is still up keeps its own undo.

    The overlay queues the second toast behind the first. When the first one
    times out, its dismissal used to commit whatever was pending at that
    moment: the second batch, deleted before its own Undo was even shown.
    """
    from gi.repository import Adw

    from sysbar.ui.shelf.shelf_window import ShelfWindow

    service = ShelfService(data_dir=tmp_path / "shelf")
    service.add_text(text="First batch")
    window = ShelfWindow(service=service)
    toasts: list[Adw.Toast] = []
    add_toast = window._toasts.add_toast

    def record(toast: Adw.Toast) -> None:
        toasts.append(toast)
        add_toast(toast)

    window._toasts.add_toast = record
    try:
        window._on_clear(None)
        second = service.add_text(text="Second batch")
        window._on_clear(None)

        toasts[0].dismiss()  # the first toast times out
        _drain_main_loop()
        toasts[1].emit("button-clicked")

        assert service.items == [second]
    finally:
        window.destroy()


def test_uninstaller_chooses_app_and_reports_removal(gtk: object, tmp_path: Path) -> None:
    from gi.repository import Gio

    from sysbar.ui.uninstall.uninstaller_window import UninstallerWindow

    residue = tmp_path / ".config" / "SysbarSmoke"
    residue.mkdir(parents=True)
    (residue / "settings").write_bytes(b"data")
    window = UninstallerWindow(
        uninstaller=AppUninstaller(
            home=tmp_path, trash=_FakeTrash(), remover=_FakeRemover(), polkit_available=False
        ),
        query=_FakePackageQuery(),
    )
    try:
        window._apps = [Gio.AppInfo.create_from_commandline("/bin/true", "SysbarSmoke", 0)]
        window._fill_app_list()
        window._on_app_chosen(window._app_list, window._app_list.get_row_at_index(0))
        assert window._target is not None
        assert window._target.name == "SysbarSmoke"
        assert len(window._switches) == 1
        assert window._switches[0][1].get_subtitle() == f"4 B · {residue}"
        assert window._remove_button.get_sensitive() is True
        window._on_remove(None)
        assert window._status.get_label() == "Done: 4 B moved to the Trash"
    finally:
        window.destroy()


def test_mixer_section_unavailable_message_is_translated(gtk: object, tmp_path: Path) -> None:
    """The recording gate only sees strings routed through ``_()``, so check the render.

    A literal handed to ``set_title`` never reaches the recorder, which is how
    an English message stayed in the Italian UI. Here the real catalog is compiled
    and installed, and the row's title is read back.
    """
    import gettext
    import shutil
    import subprocess

    from sysbar.core import i18n
    from sysbar.ui.panel.mixer_section import MixerSection

    msgfmt = shutil.which("msgfmt")
    if msgfmt is None:
        pytest.skip("msgfmt not available")
    po = Path(__file__).resolve().parents[2] / "data/locale/it/LC_MESSAGES/sysbar.po"
    mo = tmp_path / "sysbar.mo"
    subprocess.run([msgfmt, "-o", str(mo), str(po)], check=True)
    saved = i18n._translation
    with mo.open("rb") as handle:
        i18n.set_translation(gettext.GNUTranslations(handle))
    try:
        section = MixerSection()
        section.set_unavailable()
        assert section._empty.get_title() == "PipeWire/PulseAudio non disponibile"
    finally:
        i18n.set_translation(saved)
