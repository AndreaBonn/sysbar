from sysbar.app.tray.menu_builder import MenuActions, QuickToggleState, build_menu_items
from sysbar.app.tray.menu_model import TOGGLE_OFF, TOGGLE_ON, TYPE_SEPARATOR, MenuItem
from sysbar.core.constants import AUTHOR_NAME, MAX_PERIPHERAL_ROWS, TRAY_METRICS

_METRIC_SEPARATOR_INDEX = len(TRAY_METRICS) + MAX_PERIPHERAL_ROWS


def _noop() -> None:
    return None


def _actions() -> MenuActions:
    return MenuActions(
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
    )


def _build(
    metric_values: dict[str, str] | None = None,
    *,
    device_rows: tuple[str, ...] = (),
    keep_awake_on: bool = False,
    shelf_enabled: bool = False,
    clipboard_enabled: bool = False,
    toggles: QuickToggleState | None = None,
) -> list[MenuItem]:
    return build_menu_items(
        metric_values or {},
        device_rows=device_rows,
        keep_awake_on=keep_awake_on,
        shelf_enabled=shelf_enabled,
        clipboard_enabled=clipboard_enabled,
        toggles=toggles or QuickToggleState(),
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
    separator = items[_METRIC_SEPARATOR_INDEX]
    assert separator.item_type == TYPE_SEPARATOR
    assert separator.visible is False


def test_metric_separator_visible_when_metrics_present() -> None:
    items = _build({"cpu": "CPU 10%"})
    separator = items[_METRIC_SEPARATOR_INDEX]
    assert separator.visible is True


def test_device_pool_has_fixed_slot_count() -> None:
    items = _build()
    device_slots = items[len(TRAY_METRICS) : _METRIC_SEPARATOR_INDEX]
    assert len(device_slots) == MAX_PERIPHERAL_ROWS
    assert all(not slot.visible for slot in device_slots)


def test_device_rows_fill_pool_and_stay_disabled() -> None:
    items = _build(device_rows=("Keyboard 80%", "Headset 45%"))
    device_slots = items[len(TRAY_METRICS) : _METRIC_SEPARATOR_INDEX]
    visible = [slot for slot in device_slots if slot.visible]
    assert [slot.label for slot in visible] == ["Keyboard 80%", "Headset 45%"]
    assert all(slot.enabled is False for slot in visible)


def test_separator_visible_when_only_device_rows_present() -> None:
    items = _build(device_rows=("Keyboard 80%",))
    assert items[_METRIC_SEPARATOR_INDEX].visible is True


def test_node_count_constant_with_and_without_device_rows() -> None:
    assert len(_build()) == len(_build(device_rows=("Keyboard 80%", "Headset 45%")))


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


def test_clipboard_visibility_follows_flag() -> None:
    shown = next(i for i in _build(clipboard_enabled=True) if i.label == "Clipboard")
    hidden = next(i for i in _build(clipboard_enabled=False) if i.label == "Clipboard")
    assert shown.visible is True
    assert hidden.visible is False


def test_scenes_submenu_is_hidden_but_present_without_scenes() -> None:
    """The node stays in the tree so the host's ids keep their meaning."""
    items = _build()
    submenu = next(i for i in items if i.label == "Scenes")
    assert submenu.visible is False


def test_scenes_submenu_lists_entries_and_marks_active() -> None:
    from sysbar.app.tray.menu_builder import SceneMenuEntry, build_menu_items
    from sysbar.app.tray.menu_model import TOGGLE_ON

    scenes = (
        SceneMenuEntry(id="focus", name="Focus", active=True),
        SceneMenuEntry(id="relax", name="Relax", active=False),
    )
    items = build_menu_items(
        {},
        keep_awake_on=False,
        shelf_enabled=False,
        clipboard_enabled=False,
        toggles=QuickToggleState(),
        actions=_actions(),
        scenes=scenes,
    )
    submenu = next(i for i in items if i.label == "Scenes")
    child_labels = [c.label for c in submenu.children if c.label]
    assert child_labels == ["Focus", "Relax", "None"]
    focus = next(c for c in submenu.children if c.label == "Focus")
    assert focus.toggle_state == TOGGLE_ON


def test_scenes_submenu_activate_and_clear_callbacks() -> None:
    from sysbar.app.tray.menu_builder import MenuActions, SceneMenuEntry, build_menu_items

    calls: list[str] = []
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
        activate_scene=lambda scene_id: calls.append(f"activate:{scene_id}"),
        clear_scene=lambda: calls.append("clear"),
    )
    items = build_menu_items(
        {},
        keep_awake_on=False,
        shelf_enabled=False,
        clipboard_enabled=False,
        toggles=QuickToggleState(),
        actions=actions,
        scenes=(SceneMenuEntry(id="focus", name="Focus", active=False),),
    )
    submenu = next(i for i in items if i.label == "Scenes")
    focus = next(c for c in submenu.children if c.label == "Focus")
    none_row = next(c for c in submenu.children if c.label == "None")
    assert focus.action is not None and none_row.action is not None
    focus.action()
    none_row.action()
    assert calls == ["activate:focus", "clear"]


def test_action_rows_are_present_and_enabled() -> None:
    items = _build()
    labels = [i.label for i in items if i.item_type != TYPE_SEPARATOR and i.label]
    assert labels == [
        "Keep awake",
        "Mute microphone",
        "Microphone in use",
        "Turn on Do Not Disturb",
        "Switch to dark mode",
        "Scenes",
        "Open panel",
        "Open shelf",
        "Clipboard",
        "Uninstall app…",
        "Settings",
        "Quit",
        f"© {AUTHOR_NAME}",
    ]


def test_quick_toggles_hidden_when_unavailable() -> None:
    items = _build()
    for label in (
        "Mute microphone",
        "Turn on Do Not Disturb",
        "Switch to dark mode",
        "Microphone in use",
    ):
        row = next(i for i in items if i.label == label)
        assert row.visible is False


def test_quick_toggles_labels_reflect_current_state() -> None:
    toggles = QuickToggleState(
        mic_available=True,
        mic_muted=True,
        mic_in_use=True,
        dnd_available=True,
        dnd_active=True,
        dark_available=True,
        dark_active=False,
    )
    items = _build(toggles=toggles)
    # When a toggle is on, the label offers the inverse action.
    mic = next(i for i in items if i.label == "Unmute microphone")
    dnd = next(i for i in items if i.label == "Turn off Do Not Disturb")
    dark = next(i for i in items if i.label == "Switch to dark mode")
    in_use = next(i for i in items if i.label == "Microphone in use")
    assert mic.visible and mic.action is not None
    assert dnd.visible and dnd.action is not None
    assert dark.visible and dark.action is not None
    assert in_use.visible and in_use.enabled is False


def test_microphone_toggle_callback_wired() -> None:
    calls: list[str] = []
    actions = MenuActions(
        toggle_keep_awake=_noop,
        toggle_microphone=lambda: calls.append("mic"),
        toggle_dnd=lambda: calls.append("dnd"),
        toggle_dark_mode=lambda: calls.append("dark"),
        open_panel=_noop,
        open_shelf=_noop,
        open_clipboard=_noop,
        open_uninstaller=_noop,
        open_settings=_noop,
        open_github=_noop,
        quit=_noop,
    )
    items = build_menu_items(
        {},
        keep_awake_on=False,
        shelf_enabled=False,
        clipboard_enabled=False,
        toggles=QuickToggleState(mic_available=True),
        actions=actions,
    )
    mic = next(i for i in items if i.label == "Mute microphone")
    assert mic.action is not None
    mic.action()
    assert calls == ["mic"]


def test_quit_appears_exactly_once() -> None:
    items = _build({"cpu": "CPU 10%"}, keep_awake_on=True, shelf_enabled=True)
    quit_rows = [i for i in items if i.label == "Quit"]
    assert len(quit_rows) == 1


def test_action_callbacks_are_wired() -> None:
    calls: list[str] = []
    actions = MenuActions(
        toggle_keep_awake=lambda: calls.append("toggle"),
        toggle_microphone=_noop,
        toggle_dnd=_noop,
        toggle_dark_mode=_noop,
        open_panel=lambda: calls.append("panel"),
        open_shelf=lambda: calls.append("shelf"),
        open_clipboard=_noop,
        open_uninstaller=lambda: calls.append("uninstall"),
        open_settings=lambda: calls.append("settings"),
        open_github=lambda: calls.append("github"),
        quit=lambda: calls.append("quit"),
    )
    items = build_menu_items(
        {},
        keep_awake_on=False,
        shelf_enabled=False,
        clipboard_enabled=False,
        toggles=QuickToggleState(),
        actions=actions,
    )
    quit_row = next(i for i in items if i.label == "Quit")
    assert quit_row.action is not None
    quit_row.action()
    assert calls == ["quit"]


def test_github_credit_is_last_and_wired() -> None:
    calls: list[str] = []
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
        open_github=lambda: calls.append("github"),
        quit=_noop,
    )
    items = build_menu_items(
        {},
        keep_awake_on=False,
        shelf_enabled=False,
        clipboard_enabled=False,
        toggles=QuickToggleState(),
        actions=actions,
    )
    credit = items[-1]
    assert credit.label == f"© {AUTHOR_NAME}"
    assert credit.action is not None
    credit.action()
    assert calls == ["github"]
