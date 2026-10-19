from __future__ import annotations

from sysbar.app.settings_content import (
    ALERTS,
    PLACEMENT_OPTIONS,
    SHORTCUTS,
    AlertSpec,
    alert_subtitle,
    tray_preview_text,
)


def _spec(key: str) -> AlertSpec:
    return next(spec for spec in ALERTS if spec.key == key)


def test_placements_read_as_places_not_internal_states() -> None:
    assert PLACEMENT_OPTIONS == (("off", "Hidden"), ("bar", "Top bar"), ("menu", "Menu only"))


def test_every_alert_offers_a_non_zero_suggestion() -> None:
    assert len(ALERTS) == 5
    assert all(spec.suggested > 0 for spec in ALERTS)


def test_cpu_alert_subtitle_includes_how_long_the_load_must_last() -> None:
    assert alert_subtitle(_spec("alert-cpu-percent"), 90, cpu_seconds=30) == (
        "Above 90% for 30 seconds"
    )


def test_threshold_alerts_say_above_and_battery_says_below() -> None:
    assert alert_subtitle(_spec("alert-memory-percent"), 85, cpu_seconds=30) == "Above 85%"
    assert alert_subtitle(_spec("alert-temperature-celsius"), 80, cpu_seconds=30) == "Above 80°C"
    assert alert_subtitle(_spec("alert-battery-percent"), 15, cpu_seconds=30) == "Below 15%"


def test_a_zero_threshold_reads_as_off() -> None:
    assert alert_subtitle(_spec("alert-disk-percent"), 0, cpu_seconds=30) == "Not active"


def test_tray_preview_shows_the_label_or_says_the_bar_is_empty() -> None:
    assert tray_preview_text("CPU 23% · RAM 61%") == "CPU 23% · RAM 61%"
    assert tray_preview_text("") == "Only the icon: nothing is placed in the top bar"


def test_tray_preview_says_it_is_waiting_before_the_first_reading() -> None:
    assert tray_preview_text(None) == "Waiting for the first reading…"


def test_every_global_shortcut_has_a_working_command_line_equivalent() -> None:
    from sysbar.app.commands.catalogue import command_ids

    known = set(command_ids())
    assert len(SHORTCUTS) == 5
    for shortcut in SHORTCUTS:
        assert shortcut.command.startswith("sysbar ")
        assert shortcut.command.removeprefix("sysbar ") in known


def test_shortcut_commands_name_the_action_they_run() -> None:
    commands = {shortcut.key: shortcut.command for shortcut in SHORTCUTS}

    assert commands["hotkey-enabled"] == "sysbar toggle-keep-awake"
    assert commands["hotkey-palette-enabled"] == "sysbar open-palette"
