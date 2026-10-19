from __future__ import annotations

from sysbar.app.panel_summary import (
    TILE_DARK,
    TILE_DND,
    TILE_KEEP_AWAKE,
    TILE_MICROPHONE,
    battery_text,
    memory_text,
    quick_tiles,
    summarize,
)
from sysbar.app.tray.menu_builder import QuickToggleState
from sysbar.services.system_monitor.processes import ProcessUsage
from sysbar.services.system_monitor.snapshot import SystemSnapshot

_FIREFOX = ProcessUsage(pid=1, name="firefox", cpu_percent=18.2, memory_bytes=1_000)


def test_a_quiet_machine_is_all_normal_and_names_the_busiest_app() -> None:
    summary = summarize(SystemSnapshot(cpu_percent=23.0, memory_percent=61.0), _FIREFOX)

    assert summary.ok is True
    assert summary.title == "All normal"
    assert summary.detail == "Busiest app: firefox, 18% CPU"


def test_no_process_data_leaves_the_detail_empty() -> None:
    assert summarize(SystemSnapshot(cpu_percent=5.0), None).detail == ""


def test_high_cpu_is_reported_with_its_value() -> None:
    summary = summarize(SystemSnapshot(cpu_percent=95.0), _FIREFOX)

    assert summary.ok is False
    assert summary.title == "CPU busy: 95%"


def test_the_first_problem_found_wins_when_several_hold() -> None:
    snapshot = SystemSnapshot(cpu_percent=95.0, memory_percent=97.0)

    assert summarize(snapshot, None).title == "CPU busy: 95%"


def test_memory_temperature_and_battery_each_have_a_warning() -> None:
    assert summarize(SystemSnapshot(memory_percent=92.0), None).title == "Memory almost full: 92%"
    assert summarize(SystemSnapshot(cpu_temp_celsius=91.0), None).title == "Running hot: 91°C"
    low = SystemSnapshot(battery_percent=12.0, on_battery=True)
    assert summarize(low, None).title == "Battery low: 12%"


def test_a_low_battery_on_the_charger_is_not_a_warning() -> None:
    charging = SystemSnapshot(battery_percent=12.0, on_battery=False)

    assert summarize(charging, None).ok is True


def test_values_just_below_the_thresholds_are_normal() -> None:
    snapshot = SystemSnapshot(
        cpu_percent=89.0, memory_percent=89.0, cpu_temp_celsius=89.0, battery_percent=16.0
    )

    assert summarize(snapshot, None).ok is True


def test_quick_tiles_show_only_what_this_session_supports() -> None:
    tiles = quick_tiles(QuickToggleState(), keep_awake_on=False)

    assert [tile.id for tile in tiles] == [TILE_KEEP_AWAKE]


def test_quick_tiles_reflect_the_current_state_in_their_label() -> None:
    toggles = QuickToggleState(
        mic_available=True,
        mic_muted=True,
        dnd_available=True,
        dnd_active=False,
        dark_available=True,
        dark_active=True,
    )

    tiles = {tile.id: tile for tile in quick_tiles(toggles, keep_awake_on=True)}

    assert set(tiles) == {TILE_KEEP_AWAKE, TILE_MICROPHONE, TILE_DND, TILE_DARK}
    assert tiles[TILE_KEEP_AWAKE].active is True
    assert tiles[TILE_MICROPHONE].label == "Microphone"
    # Highlighted means "on" for every tile: a muted microphone is off.
    assert tiles[TILE_MICROPHONE].active is False
    assert tiles[TILE_DND].active is False
    assert tiles[TILE_DARK].active is True


def test_a_value_exactly_at_the_threshold_counts_as_a_problem() -> None:
    assert summarize(SystemSnapshot(cpu_percent=90.0), None).ok is False
    low = SystemSnapshot(battery_percent=15.0, on_battery=True)
    assert summarize(low, None).ok is False


def test_memory_pressure_is_a_problem_even_below_the_percent_threshold() -> None:
    snapshot = SystemSnapshot(memory_percent=70.0, memory_pressure="critical")

    assert summarize(snapshot, None).title == "Memory under pressure"


def test_the_hot_threshold_is_reported_in_the_chosen_unit() -> None:
    title = summarize(
        SystemSnapshot(cpu_temp_celsius=91.0), None, temperature_unit="fahrenheit"
    ).title

    assert title == "Running hot: 196°F"


def test_a_nameless_busiest_process_is_not_named() -> None:
    nameless = ProcessUsage(pid=2, name="", cpu_percent=50.0, memory_bytes=1)

    assert summarize(SystemSnapshot(cpu_percent=5.0), nameless).detail == ""


def test_memory_text_mentions_pressure_only_when_it_is_not_normal() -> None:
    assert memory_text(SystemSnapshot(memory_percent=61.0, memory_pressure="normal")) == "61%"
    high = SystemSnapshot(memory_percent=88.0, memory_pressure="warning")
    assert memory_text(high) == "88% · high pressure"
    assert memory_text(SystemSnapshot(memory_percent=50.0, memory_pressure="odd")) == "50%"
    assert memory_text(SystemSnapshot()) is None


def test_battery_text_says_whether_it_charges_or_drains() -> None:
    assert battery_text(SystemSnapshot(battery_percent=78.0, on_battery=True)) == (
        "78% · on battery"
    )
    charging = SystemSnapshot(battery_percent=40.0, battery_charging=True)
    assert battery_text(charging) == "40% · charging"
    assert battery_text(SystemSnapshot(battery_percent=100.0)) == "100%"
    assert battery_text(SystemSnapshot()) is None
