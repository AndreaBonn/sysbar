"""Behaviour of the pure config-to-tray-state derivations."""

from __future__ import annotations

import gi

gi.require_version("Gio", "2.0")
import pytest  # noqa: E402
from gi.repository import Gio  # noqa: E402

from sysbar.app import tray_state  # noqa: E402
from sysbar.app.tray_renderer import TrayOptions  # noqa: E402
from sysbar.core.config import Config  # noqa: E402
from sysbar.core.constants import (  # noqa: E402
    MEMORY_STYLE_BOTH,
    PLACEMENT_BAR,
    PLACEMENT_MENU,
    PLACEMENT_OFF,
    TEMPERATURE_FAHRENHEIT,
)
from sysbar.services.scenes.models import Scene  # noqa: E402
from sysbar.services.system_monitor.models import PeripheralBattery  # noqa: E402
from sysbar.services.system_monitor.snapshot import SystemSnapshot  # noqa: E402


@pytest.fixture
def config(compiled_schema: str) -> Config:
    return Config(backend=Gio.memory_settings_backend_new())


def _set_all_placements(config: Config, placement: str) -> None:
    for metric in ("cpu", "gpu", "memory", "network", "battery", "power"):
        config.set_string(f"menu-bar-{metric}-placement", placement)


# --- tray_options ---------------------------------------------------------


def test_tray_options_carries_the_configured_styles(config: Config) -> None:
    config.set_string("menu-bar-memory-style", MEMORY_STYLE_BOTH)
    config.set_string("temperature-unit", TEMPERATURE_FAHRENHEIT)

    options = tray_state.tray_options(config)

    assert options.memory_style == MEMORY_STYLE_BOTH
    assert options.temperature_unit == TEMPERATURE_FAHRENHEIT


def test_tray_options_carries_each_metric_placement(config: Config) -> None:
    _set_all_placements(config, PLACEMENT_OFF)
    config.set_string("menu-bar-cpu-placement", PLACEMENT_BAR)

    options = tray_state.tray_options(config)

    assert options.cpu == PLACEMENT_BAR
    assert options.memory == PLACEMENT_OFF


# --- graph_metrics --------------------------------------------------------


def test_graph_metrics_is_empty_when_no_sparkline_is_enabled(config: Config) -> None:
    for metric in ("cpu", "gpu", "memory", "network", "power", "battery"):
        config.set_bool(f"monitor-graph-{metric}", False)

    assert tray_state.graph_metrics(config) == frozenset()


def test_graph_metrics_lists_only_the_enabled_ones(config: Config) -> None:
    for metric in ("cpu", "gpu", "memory", "network", "power", "battery"):
        config.set_bool(f"monitor-graph-{metric}", False)
    config.set_bool("monitor-graph-cpu", True)
    config.set_bool("monitor-graph-network", True)

    assert tray_state.graph_metrics(config) == frozenset({"cpu", "network"})


# --- has_menu_metrics and wants_tray_sampling -----------------------------


def test_has_menu_metrics_is_false_when_everything_is_in_the_bar(config: Config) -> None:
    _set_all_placements(config, PLACEMENT_BAR)

    assert tray_state.has_menu_metrics(config) is False


def test_has_menu_metrics_is_true_for_a_single_menu_placement(config: Config) -> None:
    _set_all_placements(config, PLACEMENT_BAR)
    config.set_string("menu-bar-power-placement", PLACEMENT_MENU)

    assert tray_state.has_menu_metrics(config) is True


def test_tray_sampling_stops_with_everything_off_and_no_device_batteries(config: Config) -> None:
    _set_all_placements(config, PLACEMENT_OFF)
    config.set_bool("menu-show-device-batteries", False)

    assert tray_state.wants_tray_sampling(config) is False


def test_tray_sampling_runs_for_device_batteries_alone(config: Config) -> None:
    _set_all_placements(config, PLACEMENT_OFF)
    config.set_bool("menu-show-device-batteries", True)

    assert tray_state.wants_tray_sampling(config) is True


def test_tray_sampling_runs_for_a_single_placed_metric(config: Config) -> None:
    _set_all_placements(config, PLACEMENT_OFF)
    config.set_bool("menu-show-device-batteries", False)
    config.set_string("menu-bar-cpu-placement", PLACEMENT_MENU)

    assert tray_state.wants_tray_sampling(config) is True


# --- menu_metrics and menu_device_rows ------------------------------------


def test_menu_metrics_is_empty_without_a_snapshot() -> None:
    assert tray_state.menu_metrics(None, TrayOptions()) == {}


def test_menu_metrics_renders_the_metrics_placed_in_the_menu() -> None:
    snapshot = SystemSnapshot(cpu_percent=42.0)

    values = tray_state.menu_metrics(snapshot, TrayOptions(cpu=PLACEMENT_MENU))

    assert "cpu" in values
    assert "42" in values["cpu"]


def test_menu_device_rows_is_empty_when_the_toggle_is_off(config: Config) -> None:
    config.set_bool("menu-show-device-batteries", False)
    snapshot = SystemSnapshot(
        peripherals=(PeripheralBattery(model="M", kind=5, percent=80.0, charging=False),)
    )

    assert tray_state.menu_device_rows(config, snapshot) == ()


def test_menu_device_rows_is_empty_without_a_snapshot(config: Config) -> None:
    config.set_bool("menu-show-device-batteries", True)

    assert tray_state.menu_device_rows(config, None) == ()


def test_menu_device_rows_renders_one_row_per_peripheral(config: Config) -> None:
    config.set_bool("menu-show-device-batteries", True)
    snapshot = SystemSnapshot(
        peripherals=(
            PeripheralBattery(model="M", kind=5, percent=80.0, charging=False),
            PeripheralBattery(model="K", kind=6, percent=55.0, charging=False),
        )
    )

    rows = tray_state.menu_device_rows(config, snapshot)

    assert len(rows) == 2


# --- unavailable_metrics --------------------------------------------------


def test_unavailable_metrics_fails_open_without_a_snapshot() -> None:
    assert tray_state.unavailable_metrics(None) == frozenset()


def test_unavailable_metrics_reports_hardware_absent_from_the_snapshot() -> None:
    snapshot = SystemSnapshot(cpu_percent=10.0)

    unavailable = tray_state.unavailable_metrics(snapshot)

    assert "gpu" in unavailable
    assert "battery" in unavailable


def test_unavailable_metrics_omits_hardware_present_in_the_snapshot() -> None:
    snapshot = SystemSnapshot(cpu_percent=10.0, battery_percent=64.0)

    assert "battery" not in tray_state.unavailable_metrics(snapshot)


# --- countdown_text -------------------------------------------------------


def test_countdown_text_is_empty_when_keep_awake_is_off() -> None:
    assert tray_state.countdown_text(active=False, show=True, remaining_seconds=90) == ""


def test_countdown_text_is_empty_when_the_countdown_is_disabled() -> None:
    assert tray_state.countdown_text(active=True, show=False, remaining_seconds=90) == ""


def test_countdown_text_is_the_bare_marker_for_an_indefinite_session() -> None:
    assert tray_state.countdown_text(active=True, show=True, remaining_seconds=None) == "▶"


def test_countdown_text_appends_the_formatted_remaining_time() -> None:
    text = tray_state.countdown_text(active=True, show=True, remaining_seconds=90)

    assert text.startswith("▶ ")
    assert text != "▶"


# --- scene_entries --------------------------------------------------------


def _scene(scene_id: str, name: str) -> Scene:
    return Scene(id=scene_id, name=name)


def test_scene_entries_is_empty_for_no_scenes() -> None:
    assert tray_state.scene_entries([], active_id="focus") == ()


def test_scene_entries_flags_only_the_active_scene() -> None:
    scenes = [_scene("focus", "Focus"), _scene("presentation", "Presentation")]

    entries = tray_state.scene_entries(scenes, active_id="presentation")

    assert [(entry.id, entry.active) for entry in entries] == [
        ("focus", False),
        ("presentation", True),
    ]


def test_scene_entries_flags_none_when_no_scene_is_active() -> None:
    scenes = [_scene("focus", "Focus")]

    entries = tray_state.scene_entries(scenes, active_id="")

    assert entries[0].active is False
