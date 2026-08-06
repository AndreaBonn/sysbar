"""The tray must keep a constant node count as the scene list changes.

The dbusmenu host caches item state by id and assigns ids by position, so a tree
whose node count varies between updates makes stale ``enabled``/``label`` values
bleed onto whichever item inherited a recycled id. With three hard-coded presets
the count happened to be constant; once the user can define scenes it is not,
unless the rows come from a fixed pool.
"""

from __future__ import annotations

import gettext
from collections.abc import Iterator

import pytest

from sysbar.app.tray.menu_builder import (
    MenuActions,
    QuickToggleState,
    SceneMenuEntry,
    build_menu_items,
)
from sysbar.app.tray.menu_model import MenuItem
from sysbar.core import i18n
from sysbar.core.constants import MAX_SCENE_ROWS


def _noop() -> None: ...


def _noop_scene(_scene_id: str) -> None: ...


@pytest.fixture
def actions() -> MenuActions:
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
        activate_scene=_noop_scene,
        clear_scene=_noop,
    )


def _scenes(count: int) -> tuple[SceneMenuEntry, ...]:
    return tuple(
        SceneMenuEntry(id=f"scene-{index}", name=f"Scene {index}", active=index == 0)
        for index in range(count)
    )


def _build(actions: MenuActions, scenes: tuple[SceneMenuEntry, ...]) -> list[MenuItem]:
    return build_menu_items(
        {},
        keep_awake_on=False,
        shelf_enabled=True,
        clipboard_enabled=True,
        toggles=QuickToggleState(),
        actions=actions,
        scenes=scenes,
    )


def _count_nodes(items: list[MenuItem]) -> int:
    return sum(1 + _count_nodes(list(item.children)) for item in items)


def test_node_count_is_identical_with_no_scenes_and_with_presets(actions: MenuActions) -> None:
    assert _count_nodes(_build(actions, ())) == _count_nodes(_build(actions, _scenes(3)))


def test_node_count_is_identical_with_three_and_with_many_scenes(actions: MenuActions) -> None:
    assert _count_nodes(_build(actions, _scenes(3))) == _count_nodes(_build(actions, _scenes(12)))


def test_node_count_is_identical_at_and_beyond_the_pool_limit(actions: MenuActions) -> None:
    at_limit = _count_nodes(_build(actions, _scenes(MAX_SCENE_ROWS)))
    beyond = _count_nodes(_build(actions, _scenes(MAX_SCENE_ROWS + 5)))

    assert at_limit == beyond


def _scene_rows(items: list[MenuItem]) -> list[MenuItem]:
    submenu = next(item for item in items if item.children)
    return list(submenu.children)


def test_unused_scene_slots_are_hidden_rather_than_dropped(actions: MenuActions) -> None:
    rows = _scene_rows(_build(actions, _scenes(2)))
    slots = rows[:MAX_SCENE_ROWS]

    assert [slot.visible for slot in slots[:2]] == [True, True]
    assert not any(slot.visible for slot in slots[2:])


def test_scenes_beyond_the_pool_are_not_shown(actions: MenuActions) -> None:
    rows = _scene_rows(_build(actions, _scenes(MAX_SCENE_ROWS + 3)))
    labels = [slot.label for slot in rows[:MAX_SCENE_ROWS]]

    assert f"Scene {MAX_SCENE_ROWS}" not in labels


def test_the_scenes_submenu_is_hidden_when_there_are_no_scenes(actions: MenuActions) -> None:
    submenu = next(item for item in _build(actions, ()) if item.children)

    assert submenu.visible is False


class _RecordingTranslation(gettext.NullTranslations):
    """Records every message routed through ``_`` and echoes it back."""

    def __init__(self) -> None:
        super().__init__()
        self.seen: set[str] = set()

    def gettext(self, message: str) -> str:
        self.seen.add(message)
        return message


@pytest.fixture
def recorder() -> Iterator[_RecordingTranslation]:
    saved = i18n._translation
    recording = _RecordingTranslation()
    i18n.set_translation(recording)
    try:
        yield recording
    finally:
        i18n.set_translation(saved)


def test_scene_names_never_reach_gettext(
    actions: MenuActions, recorder: _RecordingTranslation
) -> None:
    """A user-chosen name must not become a msgid the catalogue gate demands."""
    user_named = (SceneMenuEntry(id="mine", name="Riunione col cliente", active=False),)

    _build(actions, user_named)

    assert "Riunione col cliente" not in recorder.seen
