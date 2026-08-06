"""Every command is wired to something, and to the right something.

``install_actions`` raises on an incomplete map, which fails the application at
startup rather than publishing a dead action on the bus. That is the right last
line of defence, but it only fires when the application actually starts. These
tests make the same mistake fail in CI instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest

from sysbar.app.commands import CATALOGUE, CommandId
from sysbar.app.commands.wiring import build_handlers, current_state
from sysbar.app.tray.menu_builder import QuickToggleState


class _Recorder:
    """Stands in for a feature, recording which of its methods was called."""

    def __init__(self, calls: list[str], name: str) -> None:
        self._calls = calls
        self._name = name

    def __getattr__(self, attribute: str) -> Any:
        def call(*args: object) -> None:
            suffix = f":{args[0]}" if args else ""
            self._calls.append(f"{self._name}.{attribute}{suffix}")

        return call


@dataclass
class _FakeToggles:
    calls: list[str]
    toggle_state: QuickToggleState

    def state(self) -> QuickToggleState:
        return self.toggle_state

    def toggle_microphone(self) -> None:
        self.calls.append("toggles.toggle_microphone")

    def toggle_do_not_disturb(self) -> None:
        self.calls.append("toggles.toggle_do_not_disturb")

    def toggle_dark_mode(self) -> None:
        self.calls.append("toggles.toggle_dark_mode")


@dataclass
class _FakeSwitchable:
    calls: list[str]
    name: str
    is_enabled: bool

    def open(self) -> None:
        self.calls.append(f"{self.name}.open")


def _features(
    calls: list[str],
    *,
    toggle_state: QuickToggleState = QuickToggleState(),
    shelf_enabled: bool = False,
    clipboard_enabled: bool = False,
) -> Any:
    @dataclass
    class _Features:
        panel: Any
        palette: Any
        keep_awake: Any
        toggles: Any
        scenes: Any
        shelf: Any
        clipboard: Any
        uninstaller: Any

    return _Features(
        panel=_Recorder(calls, "panel"),
        palette=_Recorder(calls, "palette"),
        keep_awake=_Recorder(calls, "keep_awake"),
        toggles=_FakeToggles(calls, toggle_state),
        scenes=_Recorder(calls, "scenes"),
        shelf=_FakeSwitchable(calls, "shelf", shelf_enabled),
        clipboard=_FakeSwitchable(calls, "clipboard", clipboard_enabled),
        uninstaller=_Recorder(calls, "uninstaller"),
    )


@pytest.fixture
def calls() -> list[str]:
    return []


def _handlers(calls: list[str]) -> Any:
    return build_handlers(
        cast(Any, _features(calls)), lambda: calls.append("settings"), lambda: calls.append("quit")
    )


# --- completeness ---------------------------------------------------------


def test_every_command_in_the_catalogue_has_a_handler(calls: list[str]) -> None:
    assert _handlers(calls).missing() == []


def test_no_command_is_wired_to_the_wrong_handler_kind(calls: list[str]) -> None:
    assert _handlers(calls).misplaced() == []


def test_the_handler_map_covers_the_whole_enum(calls: list[str]) -> None:
    handlers = _handlers(calls)

    assert set(handlers.simple) | set(handlers.parametric) == set(CommandId)


def test_the_only_parametric_handler_is_activate_scene(calls: list[str]) -> None:
    assert set(_handlers(calls).parametric) == {CommandId.ACTIVATE_SCENE}


# --- routing --------------------------------------------------------------


@pytest.mark.parametrize(
    ("command_id", "expected"),
    [
        (CommandId.OPEN_PANEL, "panel.open"),
        (CommandId.OPEN_PALETTE, "palette.open"),
        (CommandId.OPEN_SHELF, "shelf.open"),
        (CommandId.OPEN_CLIPBOARD, "clipboard.open"),
        (CommandId.OPEN_UNINSTALLER, "uninstaller.open"),
        (CommandId.TOGGLE_KEEP_AWAKE, "keep_awake.toggle"),
        (CommandId.TOGGLE_MICROPHONE, "toggles.toggle_microphone"),
        (CommandId.TOGGLE_DND, "toggles.toggle_do_not_disturb"),
        (CommandId.TOGGLE_DARK_MODE, "toggles.toggle_dark_mode"),
        (CommandId.TOGGLE_FOCUS_SCENE, "scenes.toggle_focus"),
        (CommandId.CLEAR_SCENE, "scenes.clear"),
    ],
)
def test_each_command_reaches_its_own_feature(
    calls: list[str], command_id: CommandId, expected: str
) -> None:
    _handlers(calls).simple[command_id]()

    assert calls == [expected]


def test_settings_and_quit_come_from_the_application(calls: list[str]) -> None:
    handlers = _handlers(calls)

    handlers.simple[CommandId.OPEN_SETTINGS]()
    handlers.simple[CommandId.QUIT]()

    assert calls == ["settings", "quit"]


def test_activate_scene_passes_the_scene_id_through(calls: list[str]) -> None:
    _handlers(calls).parametric[CommandId.ACTIVATE_SCENE]("focus")

    assert calls == ["scenes.activate:focus"]


# --- state ----------------------------------------------------------------


def test_state_reports_no_capabilities_by_default(calls: list[str]) -> None:
    state = current_state(cast(Any, _features(calls)))

    assert state.has_microphone is False
    assert state.has_desktop_toggles is False
    assert state.shelf_enabled is False
    assert state.clipboard_enabled is False


def test_state_reflects_an_available_microphone(calls: list[str]) -> None:
    features = _features(calls, toggle_state=QuickToggleState(mic_available=True))

    assert current_state(cast(Any, features)).has_microphone is True


def test_state_maps_desktop_toggles_to_the_do_not_disturb_backend(calls: list[str]) -> None:
    features = _features(calls, toggle_state=QuickToggleState(dnd_available=True))

    assert current_state(cast(Any, features)).has_desktop_toggles is True


def test_state_follows_the_shelf_and_clipboard_settings(calls: list[str]) -> None:
    features = _features(calls, shelf_enabled=True, clipboard_enabled=True)

    state = current_state(cast(Any, features))

    assert state.shelf_enabled is True
    assert state.clipboard_enabled is True


def test_the_catalogue_and_the_wiring_stay_the_same_size(calls: list[str]) -> None:
    handlers = _handlers(calls)

    assert len(handlers.simple) + len(handlers.parametric) == len(CATALOGUE)
