"""Editing a scene without losing what the form cannot show."""

from __future__ import annotations

from sysbar.services.scenes.actions import (
    SetOutputDevice,
    SetSetting,
    SetToggle,
    SystemToggle,
)
from sysbar.services.scenes.editing import (
    SceneDraft,
    actions_from,
    apply_draft,
    draft_from,
)
from sysbar.services.scenes.models import PRESET_SCENES, Scene, SceneOrigin


def _scene(*actions: object) -> Scene:
    return Scene(id="focus", name="Focus", actions=tuple(actions))  # type: ignore[arg-type]


# --- reading a scene into the form ----------------------------------------


def test_the_draft_carries_the_name() -> None:
    assert draft_from(_scene()).name == "Focus"


def test_a_toggle_action_becomes_a_toggle_in_the_draft() -> None:
    draft = draft_from(_scene(SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=True)))

    assert draft.toggles == {SystemToggle.KEEP_AWAKE: True}


def test_a_toggle_the_scene_does_not_set_is_absent_from_the_draft() -> None:
    draft = draft_from(_scene(SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=False)))

    assert SystemToggle.DO_NOT_DISTURB not in draft.toggles


def test_an_output_device_action_becomes_the_drafts_device() -> None:
    draft = draft_from(_scene(SetOutputDevice(device="hdmi")))

    assert draft.output_device == "hdmi"


def test_an_action_the_form_cannot_show_is_preserved() -> None:
    setting = SetSetting(key="alert-enabled", value=False)

    draft = draft_from(_scene(setting))

    assert draft.preserved == (setting,)
    assert draft.preserved_count == 1


def test_a_scene_with_no_actions_yields_an_empty_draft() -> None:
    draft = draft_from(_scene())

    assert draft.toggles == {}
    assert draft.output_device is None
    assert draft.preserved == ()


# --- writing the form back into a scene -----------------------------------


def test_a_draft_toggle_becomes_a_toggle_action() -> None:
    draft = SceneDraft(name="X", toggles={SystemToggle.DO_NOT_DISTURB: True})

    assert actions_from(draft) == (SetToggle(toggle=SystemToggle.DO_NOT_DISTURB, value=True),)


def test_a_draft_device_becomes_an_output_action() -> None:
    draft = SceneDraft(name="X", output_device="hdmi")

    assert actions_from(draft) == (SetOutputDevice(device="hdmi"),)


def test_an_empty_device_produces_no_action() -> None:
    assert actions_from(SceneDraft(name="X", output_device="")) == ()


def test_preserved_actions_come_back_out() -> None:
    setting = SetSetting(key="alert-enabled", value=False)
    draft = SceneDraft(name="X", preserved=(setting,))

    assert actions_from(draft) == (setting,)


def test_the_rebuilt_order_is_stable() -> None:
    draft = SceneDraft(
        name="X",
        toggles={
            SystemToggle.MICROPHONE_MUTED: True,
            SystemToggle.KEEP_AWAKE: False,
        },
    )

    first = actions_from(draft)
    second = actions_from(draft)

    assert first == second
    assert first[0] == SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=False)


# --- the round trip that matters ------------------------------------------


def test_editing_only_the_name_keeps_every_action() -> None:
    """The bug this module exists to prevent."""
    original = PRESET_SCENES[0]
    draft = draft_from(original)

    edited = apply_draft(
        original,
        SceneDraft(
            name="Concentrazione",
            toggles=draft.toggles,
            output_device=draft.output_device,
            preserved=draft.preserved,
        ),
    )

    assert set(edited.actions) == set(original.actions)
    assert edited.name == "Concentrazione"


def test_every_preset_survives_an_untouched_edit() -> None:
    for preset in PRESET_SCENES:
        assert set(apply_draft(preset, draft_from(preset)).actions) == set(preset.actions)


def test_editing_makes_a_built_in_a_user_scene() -> None:
    edited = apply_draft(PRESET_SCENES[0], draft_from(PRESET_SCENES[0]))

    assert edited.origin is SceneOrigin.USER
    assert edited.id == PRESET_SCENES[0].id


def test_clearing_a_toggle_removes_only_that_action() -> None:
    scene = _scene(
        SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=True),
        SetToggle(toggle=SystemToggle.DO_NOT_DISTURB, value=True),
        SetSetting(key="alert-enabled", value=False),
    )
    draft = draft_from(scene).with_toggle(SystemToggle.DO_NOT_DISTURB, None)

    actions = apply_draft(scene, draft).actions

    assert SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=True) in actions
    assert SetToggle(toggle=SystemToggle.DO_NOT_DISTURB, value=True) not in actions
    assert SetSetting(key="alert-enabled", value=False) in actions


def test_setting_a_toggle_that_was_unset_adds_it() -> None:
    draft = SceneDraft(name="X").with_toggle(SystemToggle.KEEP_AWAKE, True)

    assert draft.toggles == {SystemToggle.KEEP_AWAKE: True}


def test_with_toggle_does_not_mutate_the_original_draft() -> None:
    original = SceneDraft(name="X", toggles={SystemToggle.KEEP_AWAKE: True})

    original.with_toggle(SystemToggle.KEEP_AWAKE, None)

    assert original.toggles == {SystemToggle.KEEP_AWAKE: True}
