from collections.abc import Callable
from typing import cast

import gi
from pytest_mock import MockerFixture

gi.require_version("GLib", "2.0")
from gi.repository import GLib  # noqa: E402

from sysbar.app.tray.dbus_menu import DBusMenuServer, _to_variant  # noqa: E402
from sysbar.app.tray.menu_model import ROOT_ID, MenuItem, MenuModel  # noqa: E402

GLibVariant = GLib.Variant


def test_to_variant_bool_uses_boolean_type() -> None:
    variant = _to_variant(True)
    assert variant.get_type_string() == "b"
    assert variant.unpack() is True


def test_to_variant_int_uses_int32_type() -> None:
    variant = _to_variant(7)
    assert variant.get_type_string() == "i"
    assert variant.unpack() == 7


def test_to_variant_str_uses_string_type() -> None:
    variant = _to_variant("hello")
    assert variant.get_type_string() == "s"
    assert variant.unpack() == "hello"


def test_to_variant_other_value_stringified() -> None:
    variant = _to_variant(3.5)
    assert variant.get_type_string() == "s"
    assert variant.unpack() == "3.5"


def _server_with_model(model: MenuModel) -> DBusMenuServer:
    server = DBusMenuServer(object_path="/MenuBar")
    server.set_model(model)
    return server


def test_build_item_recurse_all_includes_nested_children() -> None:
    model = MenuModel(
        [
            MenuItem(
                label="Parent",
                children=[MenuItem(label="Child")],
            )
        ]
    )
    server = _server_with_model(model)
    parent = model.get(1)
    assert parent is not None

    item_id, _props, children = server._build_item(parent, -1, [])

    assert item_id == 1
    assert len(children) == 1
    child_id, _child_props, grandchildren = children[0].unpack()
    assert child_id == 2
    assert grandchildren == []


def test_build_item_depth_zero_emits_no_children() -> None:
    model = MenuModel([MenuItem(label="Parent", children=[MenuItem(label="Child")])])
    server = _server_with_model(model)
    parent = model.get(1)
    assert parent is not None

    _id, _props, children = server._build_item(parent, 0, [])

    assert children == []


def test_build_item_depth_one_stops_at_first_level() -> None:
    model = MenuModel(
        [
            MenuItem(
                label="Parent",
                children=[MenuItem(label="Child", children=[MenuItem(label="Grandchild")])],
            )
        ]
    )
    server = _server_with_model(model)
    parent = model.get(1)
    assert parent is not None

    _id, _props, children = server._build_item(parent, 1, [])

    assert len(children) == 1
    _child_id, _child_props, grandchildren = children[0].unpack()
    assert grandchildren == []


def test_build_item_emits_hidden_children() -> None:
    model = MenuModel(
        [MenuItem(label="Parent", children=[MenuItem(label="Hidden", visible=False)])]
    )
    server = _server_with_model(model)
    parent = model.get(1)
    assert parent is not None

    _id, _props, children = server._build_item(parent, -1, [])

    assert len(children) == 1
    _child_id, child_props, _grandchildren = children[0].unpack()
    assert child_props["visible"] is False


def test_props_variant_returns_all_when_names_empty() -> None:
    model = MenuModel([MenuItem(label="Quit")])
    server = _server_with_model(model)
    item = model.get(1)
    assert item is not None

    props = server._props_variant(item, [])

    assert props["label"].unpack() == "Quit"
    assert props["enabled"].unpack() is True


def test_props_variant_filters_by_names() -> None:
    model = MenuModel([MenuItem(label="Quit")])
    server = _server_with_model(model)
    item = model.get(1)
    assert item is not None

    props = server._props_variant(item, ["label"])

    assert set(props.keys()) == {"label"}
    assert props["label"].unpack() == "Quit"


def test_handle_about_to_show_returns_false_when_no_callback() -> None:
    server = DBusMenuServer(object_path="/MenuBar")
    assert server._handle_about_to_show(ROOT_ID) is False


def test_handle_about_to_show_returns_callback_result_as_bool() -> None:
    callback: Callable[[], bool] = lambda: True  # noqa: E731
    server = DBusMenuServer(object_path="/MenuBar", on_about_to_show=callback)
    assert server._handle_about_to_show(ROOT_ID) is True


def test_handle_about_to_show_coerces_truthy_result_to_bool() -> None:
    # The callback returns a non-bool truthy value to verify the bool() coercion
    # in _handle_about_to_show; cast keeps the static type honest.
    returns_int: Callable[[], int] = lambda: 1  # noqa: E731
    callback = cast("Callable[[], bool]", returns_int)
    server = DBusMenuServer(object_path="/MenuBar", on_about_to_show=callback)
    result = server._handle_about_to_show(ROOT_ID)
    assert result is True


def test_handle_about_to_show_submenu_skips_refresh() -> None:
    # A submenu open must not trigger the full-menu refresh: doing so emits a
    # root LayoutUpdated that cancels the host's in-progress submenu open.
    calls: list[int] = []
    callback: Callable[[], bool] = lambda: bool(calls.append(1)) or True  # noqa: E731
    server = DBusMenuServer(object_path="/MenuBar", on_about_to_show=callback)
    submenu_id = ROOT_ID + 1

    result = server._handle_about_to_show(submenu_id)

    assert result is False
    assert calls == []


def test_on_event_non_clicked_does_not_dispatch(mocker: MockerFixture) -> None:
    calls: list[str] = []
    model = MenuModel([MenuItem(label="A", action=lambda: calls.append("a"))])
    server = _server_with_model(model)
    idle_add = mocker.patch("sysbar.app.tray.dbus_menu.GLib.idle_add")

    server._on_event(1, "hovered", None, 0)

    idle_add.assert_not_called()
    assert calls == []


def test_on_event_clicked_dispatches_action_via_idle_add(mocker: MockerFixture) -> None:
    model = MenuModel([MenuItem(label="A", action=lambda: None)])
    server = _server_with_model(model)
    idle_add = mocker.patch("sysbar.app.tray.dbus_menu.GLib.idle_add")

    server._on_event(1, "clicked", None, 0)

    idle_add.assert_called_once()
    args = idle_add.call_args.args
    assert args[0] == server._invoke
    assert args[1] == model.action_for(1)


def test_on_event_clicked_without_action_does_not_dispatch(mocker: MockerFixture) -> None:
    model = MenuModel([MenuItem(label="A")])
    server = _server_with_model(model)
    idle_add = mocker.patch("sysbar.app.tray.dbus_menu.GLib.idle_add")

    server._on_event(1, "clicked", None, 0)

    idle_add.assert_not_called()


def test_invoke_calls_action_and_returns_false() -> None:
    calls: list[str] = []
    result = DBusMenuServer._invoke(lambda: calls.append("done"))
    assert calls == ["done"]
    assert result is False


def test_invoke_non_callable_returns_false() -> None:
    assert DBusMenuServer._invoke(None) is False


# --------------------------------------------------------------------------- #
# register / unregister / set_model — Gio.DBusConnection interaction
# --------------------------------------------------------------------------- #


class FakeConnection:
    """Minimal stand-in for ``Gio.DBusConnection``."""

    def __init__(self, registration_id: int = 99) -> None:
        self._registration_id = registration_id
        self.registered: list[str] = []
        self.unregistered: list[int] = []
        self.emitted: list[tuple[object, ...]] = []

    def register_object(
        self, path: str, _iface: object, _handler: object, _a: object, _b: object
    ) -> int:
        self.registered.append(path)
        return self._registration_id

    def unregister_object(self, registration_id: int) -> None:
        self.unregistered.append(registration_id)

    def emit_signal(self, *args: object) -> None:
        self.emitted.append(args)


def test_register_stores_connection_and_registration_id() -> None:
    server = DBusMenuServer(object_path="/MenuBar")
    connection = FakeConnection(registration_id=42)

    server.register(connection)

    assert connection.registered == ["/MenuBar"]
    assert server._registration_id == 42
    assert server._connection is connection


def test_unregister_releases_object_when_registered() -> None:
    server = DBusMenuServer(object_path="/MenuBar")
    connection = FakeConnection(registration_id=42)
    server.register(connection)

    server.unregister()

    assert connection.unregistered == [42]
    assert server._registration_id == 0


def test_unregister_noop_when_not_registered() -> None:
    server = DBusMenuServer(object_path="/MenuBar")
    connection = FakeConnection()
    server._connection = connection

    server.unregister()

    assert connection.unregistered == []


def test_set_model_emits_layout_and_properties_updates_when_connected() -> None:
    server = DBusMenuServer(object_path="/MenuBar")
    connection = FakeConnection()
    server.register(connection)

    server.set_model(MenuModel([MenuItem(label="A")]))

    signal_names = [args[3] for args in connection.emitted]
    assert signal_names == ["LayoutUpdated", "ItemsPropertiesUpdated"]


def test_properties_payload_carries_current_labels_for_all_items() -> None:
    server = DBusMenuServer(object_path="/MenuBar")
    server.set_model(MenuModel([MenuItem(label="Mute microphone"), MenuItem(label="Open panel")]))

    payload = server._properties_payload()

    labels = [props["label"].get_string() for _id, props in payload]
    assert labels == ["Mute microphone", "Open panel"]


def test_properties_payload_reflects_a_relabelled_item() -> None:
    server = DBusMenuServer(object_path="/MenuBar")
    server.set_model(MenuModel([MenuItem(label="Mute microphone")]))
    server.set_model(MenuModel([MenuItem(label="Unmute microphone")]))

    labels = [props["label"].get_string() for _id, props in server._properties_payload()]
    assert labels == ["Unmute microphone"]


def test_set_model_skips_emit_when_not_connected() -> None:
    server = DBusMenuServer(object_path="/MenuBar")

    server.set_model(MenuModel([MenuItem(label="A")]))

    assert server._connection is None


# --------------------------------------------------------------------------- #
# _get_layout / _get_group_properties / _get_property
# --------------------------------------------------------------------------- #


def test_get_layout_returns_revision_and_root_when_parent_unknown() -> None:
    model = MenuModel([MenuItem(label="A")])
    server = _server_with_model(model)

    revision, layout = server._get_layout(404, -1, []).unpack()

    assert revision == server._revision
    root_id, _props, children = layout
    assert root_id == 0
    assert len(children) == 1


def test_get_group_properties_returns_entries_for_known_ids() -> None:
    model = MenuModel([MenuItem(label="A"), MenuItem(label="B")])
    server = _server_with_model(model)

    (entries,) = server._get_group_properties([1, 2], ["label"]).unpack()

    assert [item_id for item_id, _props in entries] == [1, 2]
    assert entries[0][1]["label"] == "A"


def test_get_group_properties_skips_unknown_ids() -> None:
    model = MenuModel([MenuItem(label="A")])
    server = _server_with_model(model)

    (entries,) = server._get_group_properties([1, 999], []).unpack()

    assert [item_id for item_id, _props in entries] == [1]


def test_get_property_returns_value_for_known_item() -> None:
    model = MenuModel([MenuItem(label="Quit")])
    server = _server_with_model(model)

    (value,) = server._get_property(1, "label").unpack()

    assert value == "Quit"


def test_get_property_returns_empty_string_for_unknown_item() -> None:
    model = MenuModel([MenuItem(label="Quit")])
    server = _server_with_model(model)

    (value,) = server._get_property(999, "label").unpack()

    assert value == ""


# --------------------------------------------------------------------------- #
# _handle_method — dispatch table
# --------------------------------------------------------------------------- #


class FakeInvocation:
    def __init__(self) -> None:
        self.returned: list[object] = []
        self.errors: list[tuple[object, ...]] = []

    def return_value(self, value: object) -> None:
        self.returned.append(value)

    def return_error_literal(self, *args: object) -> None:
        self.errors.append(args)


def _dispatch(server: DBusMenuServer, method: str, params: GLib.Variant) -> FakeInvocation:
    invocation = FakeInvocation()
    server._handle_method(None, "", "", "", method, params, invocation)
    return invocation


def test_handle_method_get_layout_returns_value() -> None:
    server = _server_with_model(MenuModel([MenuItem(label="A")]))
    params = GLibVariant("(iias)", (0, -1, []))

    invocation = _dispatch(server, "GetLayout", params)

    assert len(invocation.returned) == 1
    assert invocation.errors == []


def test_handle_method_get_group_properties_returns_value() -> None:
    server = _server_with_model(MenuModel([MenuItem(label="A")]))
    params = GLibVariant("(aias)", ([1], []))

    invocation = _dispatch(server, "GetGroupProperties", params)

    assert len(invocation.returned) == 1


def test_handle_method_get_property_returns_value() -> None:
    server = _server_with_model(MenuModel([MenuItem(label="A")]))
    params = GLibVariant("(is)", (1, "label"))

    invocation = _dispatch(server, "GetProperty", params)

    assert len(invocation.returned) == 1


def test_handle_method_event_returns_none(mocker: MockerFixture) -> None:
    server = _server_with_model(MenuModel([MenuItem(label="A")]))
    mocker.patch("sysbar.app.tray.dbus_menu.GLib.idle_add")
    params = GLibVariant("(isvu)", (1, "clicked", GLibVariant("s", "x"), 0))

    invocation = _dispatch(server, "Event", params)

    assert invocation.returned == [None]


def test_handle_method_about_to_show_returns_bool_variant() -> None:
    server = DBusMenuServer(object_path="/MenuBar", on_about_to_show=lambda: True)
    server.set_model(MenuModel([MenuItem(label="A")]))
    params = GLibVariant("(i)", (0,))

    invocation = _dispatch(server, "AboutToShow", params)

    assert len(invocation.returned) == 1
    returned = cast("GLib.Variant", invocation.returned[0])
    assert returned.unpack() == (True,)


def test_handle_method_unknown_returns_error() -> None:
    server = _server_with_model(MenuModel([MenuItem(label="A")]))
    params = GLibVariant("()", ())

    invocation = _dispatch(server, "Bogus", params)

    assert invocation.returned == []
    assert len(invocation.errors) == 1
