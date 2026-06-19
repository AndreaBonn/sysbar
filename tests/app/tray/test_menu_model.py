from sysbar.app.tray.menu_model import (
    ROOT_ID,
    TOGGLE_ON,
    TYPE_SEPARATOR,
    MenuItem,
    MenuModel,
)


def _sample_model() -> MenuModel:
    return MenuModel(
        [
            MenuItem(label="Keep awake", toggle_type="checkmark", toggle_state=TOGGLE_ON),
            MenuItem(item_type=TYPE_SEPARATOR),
            MenuItem(
                label="Monitor",
                children=[MenuItem(label="Open panel"), MenuItem(label="Settings")],
            ),
        ]
    )


def test_root_has_id_zero() -> None:
    model = _sample_model()
    assert model.root.item_id == ROOT_ID


def test_ids_are_unique() -> None:
    model = _sample_model()
    ids = [item.item_id for item in (model.get(i) for i in range(6)) if item]
    assert len(set(ids)) == len(ids)


def test_ids_are_contiguous_from_zero() -> None:
    model = _sample_model()
    ids = [item.item_id for item in (model.get(i) for i in range(6)) if item]
    assert ids == [0, 1, 2, 3, 4, 5]


def test_get_unknown_id_returns_none() -> None:
    assert _sample_model().get(999) is None


def test_separator_properties_only_type_and_visible() -> None:
    model = _sample_model()
    separator = model.get(2)
    assert separator is not None
    assert model.properties(separator) == {"type": TYPE_SEPARATOR, "visible": True}


def test_toggle_properties_present() -> None:
    model = _sample_model()
    props = model.properties(model.get(1))  # type: ignore[arg-type]
    assert props["toggle-type"] == "checkmark"
    assert props["toggle-state"] == TOGGLE_ON


def test_submenu_marks_children_display() -> None:
    model = _sample_model()
    props = model.properties(model.get(3))  # type: ignore[arg-type]
    assert props["children-display"] == "submenu"


def test_action_for_invokes_correct_item() -> None:
    calls: list[str] = []
    model = MenuModel(
        [
            MenuItem(label="A", action=lambda: calls.append("a")),
            MenuItem(label="B", action=lambda: calls.append("b")),
        ]
    )
    action = model.action_for(2)  # second top-level item
    assert action is not None
    action()
    assert calls == ["b"]


def test_action_for_unknown_id_returns_none() -> None:
    assert _sample_model().action_for(999) is None


def test_icon_name_included_in_properties_when_set() -> None:
    model = MenuModel([MenuItem(label="Quit", icon_name="application-exit")])
    props = model.properties(model.get(1))  # type: ignore[arg-type]
    assert props["icon-name"] == "application-exit"


def test_icon_name_absent_from_properties_when_empty() -> None:
    model = MenuModel([MenuItem(label="Quit")])
    props = model.properties(model.get(1))  # type: ignore[arg-type]
    assert "icon-name" not in props
