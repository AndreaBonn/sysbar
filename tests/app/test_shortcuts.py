"""Behaviour of the global shortcut table."""

from __future__ import annotations

import gi

gi.require_version("Gio", "2.0")
import pytest  # noqa: E402
from gi.repository import Gio  # noqa: E402

from sysbar.app.shortcuts import (  # noqa: E402
    CLIPBOARD_ENABLED_KEY,
    FOCUS_SCENE_ENABLED_KEY,
    KEEP_AWAKE_ENABLED_KEY,
    SHELF_ENABLED_KEY,
    ShortcutTargets,
    build_hotkey_bindings,
)
from sysbar.core.config import Config  # noqa: E402
from sysbar.core.constants import (  # noqa: E402
    CLIPBOARD_SHORTCUT_ID,
    FOCUS_SCENE_SHORTCUT_ID,
    KEEP_AWAKE_SHORTCUT_ID,
    SHELF_SHORTCUT_ID,
)

_ALL_KEYS = (
    KEEP_AWAKE_ENABLED_KEY,
    SHELF_ENABLED_KEY,
    CLIPBOARD_ENABLED_KEY,
    FOCUS_SCENE_ENABLED_KEY,
)


@pytest.fixture
def config(compiled_schema: str) -> Config:
    return Config(backend=Gio.memory_settings_backend_new())


@pytest.fixture
def fired() -> list[str]:
    return []


@pytest.fixture
def targets(fired: list[str]) -> ShortcutTargets:
    return ShortcutTargets(
        toggle_keep_awake=lambda: fired.append("keep-awake"),
        open_shelf=lambda: fired.append("shelf"),
        open_clipboard=lambda: fired.append("clipboard"),
        toggle_focus_scene=lambda: fired.append("focus"),
    )


def test_every_shortcut_is_present(config: Config, targets: ShortcutTargets) -> None:
    ids = [binding.shortcut_id for binding in build_hotkey_bindings(config, targets)]

    assert ids == [
        KEEP_AWAKE_SHORTCUT_ID,
        SHELF_SHORTCUT_ID,
        CLIPBOARD_SHORTCUT_ID,
        FOCUS_SCENE_SHORTCUT_ID,
    ]


def test_every_shortcut_carries_a_description(config: Config, targets: ShortcutTargets) -> None:
    assert all(binding.description for binding in build_hotkey_bindings(config, targets))


def test_each_trigger_calls_its_own_target(
    config: Config, targets: ShortcutTargets, fired: list[str]
) -> None:
    for binding in build_hotkey_bindings(config, targets):
        binding.trigger()

    assert fired == ["keep-awake", "shelf", "clipboard", "focus"]


def test_bindings_are_disabled_when_their_setting_is_off(
    config: Config, targets: ShortcutTargets
) -> None:
    for key in _ALL_KEYS:
        config.set_bool(key, False)

    assert [binding.enabled() for binding in build_hotkey_bindings(config, targets)] == [
        False,
        False,
        False,
        False,
    ]


def test_bindings_are_enabled_when_their_setting_is_on(
    config: Config, targets: ShortcutTargets
) -> None:
    for key in _ALL_KEYS:
        config.set_bool(key, True)

    assert all(binding.enabled() for binding in build_hotkey_bindings(config, targets))


def test_each_binding_reads_only_its_own_key(config: Config, targets: ShortcutTargets) -> None:
    for key in _ALL_KEYS:
        config.set_bool(key, False)
    config.set_bool(SHELF_ENABLED_KEY, True)

    enabled = {
        binding.shortcut_id: binding.enabled() for binding in build_hotkey_bindings(config, targets)
    }

    assert enabled[SHELF_SHORTCUT_ID] is True
    assert enabled[KEEP_AWAKE_SHORTCUT_ID] is False
    assert enabled[CLIPBOARD_SHORTCUT_ID] is False


def test_the_gate_is_read_at_call_time_not_at_build_time(
    config: Config, targets: ShortcutTargets
) -> None:
    config.set_bool(KEEP_AWAKE_ENABLED_KEY, False)
    binding = build_hotkey_bindings(config, targets)[0]
    assert binding.enabled() is False

    config.set_bool(KEEP_AWAKE_ENABLED_KEY, True)

    assert binding.enabled() is True
