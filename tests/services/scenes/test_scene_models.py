"""The scene value: its invariants, fork-on-edit, and its stored form."""

from __future__ import annotations

import pytest

from sysbar.core.i18n import _
from sysbar.services.scenes.actions import SetSetting, SetToggle, SystemToggle
from sysbar.services.scenes.models import (
    PRESET_SCENE_IDS,
    PRESET_SCENES,
    Scene,
    SceneError,
    SceneOrigin,
    scene_display_name,
)


def _scene(**overrides: object) -> Scene:
    defaults: dict[str, object] = {
        "id": "focus",
        "name": "Focus",
        "actions": (SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=True),),
    }
    defaults.update(overrides)
    return Scene(**defaults)  # type: ignore[arg-type]


# --- invariants -----------------------------------------------------------


def test_a_scene_needs_an_id() -> None:
    with pytest.raises(SceneError, match="needs an id"):
        _scene(id="")


def test_a_scene_needs_a_name() -> None:
    with pytest.raises(SceneError, match="needs a name"):
        _scene(name="")


def test_a_whitespace_only_name_is_not_a_name() -> None:
    with pytest.raises(SceneError, match="needs a name"):
        _scene(name="   ")


def test_a_scene_may_have_no_actions() -> None:
    assert _scene(actions=()).actions == ()


def test_a_scene_is_built_in_by_default() -> None:
    assert _scene().is_built_in is True


# --- fork on edit ---------------------------------------------------------


def test_editing_a_built_in_produces_a_user_scene() -> None:
    edited = _scene().edited(name="Concentrazione", actions=None)

    assert edited.origin is SceneOrigin.USER
    assert edited.is_built_in is False


def test_editing_keeps_the_id_so_it_stays_an_override() -> None:
    assert _scene().edited(name="Altro", actions=None).id == "focus"


def test_editing_does_not_mutate_the_original() -> None:
    original = _scene()

    original.edited(name="Altro", actions=None)

    assert original.name == "Focus"
    assert original.origin is SceneOrigin.BUILT_IN


def test_editing_only_the_actions_keeps_the_name() -> None:
    edited = _scene().edited(actions=(SetSetting(key="alert-enabled", value=False),))

    assert edited.name == "Focus"
    assert edited.actions == (SetSetting(key="alert-enabled", value=False),)


def test_editing_only_the_name_keeps_the_actions() -> None:
    original = _scene()

    edited = original.edited(name="Altro", actions=None)

    assert edited.actions == original.actions


def test_editing_a_user_scene_leaves_it_a_user_scene() -> None:
    user = _scene(origin=SceneOrigin.USER)

    assert user.edited(name="Ancora", actions=None).origin is SceneOrigin.USER


# --- round trip -----------------------------------------------------------


def test_a_scene_survives_a_round_trip() -> None:
    scene = _scene(
        actions=(
            SetToggle(toggle=SystemToggle.DO_NOT_DISTURB, value=True),
            SetSetting(key="alert-enabled", value=False),
        ),
        origin=SceneOrigin.USER,
    )

    assert Scene.from_dict(scene.to_dict()) == scene


def test_every_preset_survives_a_round_trip() -> None:
    for preset in PRESET_SCENES:
        assert Scene.from_dict(preset.to_dict()) == preset


def test_the_stored_form_records_the_origin() -> None:
    assert _scene(origin=SceneOrigin.USER).to_dict()["origin"] == "user"


def test_stored_data_without_an_origin_is_read_as_a_user_scene() -> None:
    """A hand-written entry is the user's, not a built-in they cannot delete."""
    scene = Scene.from_dict({"id": "mine", "name": "Mia", "actions": []})

    assert scene.origin is SceneOrigin.USER


# --- corrupt data ---------------------------------------------------------


def test_actions_that_are_not_a_list_are_refused() -> None:
    with pytest.raises(SceneError, match="must be a list"):
        Scene.from_dict({"id": "x", "name": "X", "actions": "toggle"})


def test_an_unreadable_action_fails_the_whole_scene() -> None:
    with pytest.raises(SceneError, match="unknown action kind"):
        Scene.from_dict({"id": "x", "name": "X", "actions": [{"kind": "nope"}]})


def test_an_unknown_origin_is_refused() -> None:
    with pytest.raises(SceneError, match="unknown scene origin"):
        Scene.from_dict({"id": "x", "name": "X", "actions": [], "origin": "vendor"})


def test_a_stored_scene_without_a_name_is_refused() -> None:
    with pytest.raises(SceneError, match="needs a name"):
        Scene.from_dict({"id": "x", "actions": []})


# --- presets --------------------------------------------------------------


def test_every_preset_is_built_in() -> None:
    assert all(preset.is_built_in for preset in PRESET_SCENES)


def test_preset_ids_match_the_preset_list() -> None:
    assert {preset.id for preset in PRESET_SCENES} == PRESET_SCENE_IDS


def test_every_preset_does_something() -> None:
    assert all(preset.actions for preset in PRESET_SCENES)


def test_a_built_in_scene_name_is_translated() -> None:
    """Built-in names are in the catalogue; the tray, palette and window agree."""
    preset = PRESET_SCENES[0]

    assert scene_display_name(preset) == _(preset.name)


def test_a_user_scene_name_is_shown_verbatim() -> None:
    """Passing a user's own name through gettext would demand a msgid for it."""
    mine = Scene(id="mine", name="Presentation", origin=SceneOrigin.USER)

    assert scene_display_name(mine) == "Presentation"
