from sysbar.app.tray.menu_builder import MenuActions, build_menu_items
from sysbar.app.tray.menu_model import TOGGLE_OFF, TOGGLE_ON, TYPE_SEPARATOR, MenuItem
from sysbar.core.constants import TRAY_METRICS


def _noop() -> None:
    return None


def _actions() -> MenuActions:
    return MenuActions(
        toggle_keep_awake=_noop,
        open_panel=_noop,
        open_shelf=_noop,
        open_uninstaller=_noop,
        open_settings=_noop,
        quit=_noop,
    )


def _build(
    metric_values: dict[str, str] | None = None,
    *,
    keep_awake_on: bool = False,
    shelf_enabled: bool = False,
) -> list[MenuItem]:
    return build_menu_items(
        metric_values or {},
        keep_awake_on=keep_awake_on,
        shelf_enabled=shelf_enabled,
        actions=_actions(),
    )


def test_node_count_is_constant_regardless_of_state() -> None:
    empty = _build()
    full = _build({"cpu": "CPU 10%", "battery": "BAT 99%"}, keep_awake_on=True, shelf_enabled=True)
    assert len(empty) == len(full)


def test_has_one_slot_per_tray_metric() -> None:
    items = _build()
    metric_slots = items[: len(TRAY_METRICS)]
    assert len(metric_slots) == len(TRAY_METRICS)


def test_metric_slots_hidden_when_no_values() -> None:
    items = _build()
    metric_slots = items[: len(TRAY_METRICS)]
    assert all(not slot.visible for slot in metric_slots)


def test_metric_separator_hidden_when_no_menu_metrics() -> None:
    items = _build()
    separator = items[len(TRAY_METRICS)]
    assert separator.item_type == TYPE_SEPARATOR
    assert separator.visible is False


def test_metric_separator_visible_when_metrics_present() -> None:
    items = _build({"cpu": "CPU 10%"})
    separator = items[len(TRAY_METRICS)]
    assert separator.visible is True


def test_visible_metric_slot_carries_value_and_is_disabled() -> None:
    items = _build({"battery": "BAT 99%"})
    battery_index = TRAY_METRICS.index("battery")
    slot = items[battery_index]
    assert slot.visible is True
    assert slot.label == "BAT 99%"
    assert slot.enabled is False


def test_hidden_metric_slot_keeps_position_for_stable_ids() -> None:
    items = _build({"power": "5 W"})
    cpu_index = TRAY_METRICS.index("cpu")
    power_index = TRAY_METRICS.index("power")
    assert items[cpu_index].visible is False
    assert items[power_index].visible is True


def test_keep_awake_toggle_reflects_state() -> None:
    on = _build(keep_awake_on=True)
    off = _build(keep_awake_on=False)
    keep_on = next(i for i in on if i.label == "Keep awake")
    keep_off = next(i for i in off if i.label == "Keep awake")
    assert keep_on.toggle_state == TOGGLE_ON
    assert keep_off.toggle_state == TOGGLE_OFF


def test_open_shelf_visibility_follows_flag() -> None:
    shown = _build(shelf_enabled=True)
    hidden = _build(shelf_enabled=False)
    shelf_shown = next(i for i in shown if i.label == "Open shelf")
    shelf_hidden = next(i for i in hidden if i.label == "Open shelf")
    assert shelf_shown.visible is True
    assert shelf_hidden.visible is False


def test_action_rows_are_present_and_enabled() -> None:
    items = _build()
    labels = [i.label for i in items if i.item_type != TYPE_SEPARATOR and i.label]
    assert labels == [
        "Keep awake",
        "Open panel",
        "Open shelf",
        "Uninstall app…",
        "Settings",
        "Quit",
    ]


def test_quit_appears_exactly_once() -> None:
    items = _build({"cpu": "CPU 10%"}, keep_awake_on=True, shelf_enabled=True)
    quit_rows = [i for i in items if i.label == "Quit"]
    assert len(quit_rows) == 1


def test_action_callbacks_are_wired() -> None:
    calls: list[str] = []
    actions = MenuActions(
        toggle_keep_awake=lambda: calls.append("toggle"),
        open_panel=lambda: calls.append("panel"),
        open_shelf=lambda: calls.append("shelf"),
        open_uninstaller=lambda: calls.append("uninstall"),
        open_settings=lambda: calls.append("settings"),
        quit=lambda: calls.append("quit"),
    )
    items = build_menu_items({}, keep_awake_on=False, shelf_enabled=False, actions=actions)
    quit_row = next(i for i in items if i.label == "Quit")
    assert quit_row.action is not None
    quit_row.action()
    assert calls == ["quit"]
