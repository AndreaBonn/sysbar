"""Editing a scene without losing what the form cannot show."""

from __future__ import annotations

from collections.abc import MutableMapping

import pytest

from sysbar.services.scenes.actions import (
    SetOutputDevice,
    SetSetting,
    SetToggle,
    SystemToggle,
)
from sysbar.services.scenes.editing import (
    DEFAULT_BATTERY_PERCENT,
    SceneDraft,
    TriggerChoice,
    TriggerDraft,
    actions_from,
    apply_draft,
    draft_from,
    rule_from,
    rule_id_for,
    trigger_draft_from,
)
from sysbar.services.scenes.models import PRESET_SCENES, Scene, SceneOrigin
from sysbar.services.scenes.triggers import (
    BatteryBelow,
    ExternalMonitorConnected,
    OnBatteryPower,
    TriggerRule,
)


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


# --- the trigger part of the form -----------------------------------------


def test_no_rule_yields_the_empty_trigger_form() -> None:
    draft = trigger_draft_from(None)

    assert draft.choice is TriggerChoice.NEVER
    assert draft.restore_on_exit is False


def test_the_empty_form_builds_no_rule() -> None:
    assert rule_from(TriggerDraft(), "focus") is None


def test_a_monitor_rule_reads_back_as_its_choice() -> None:
    rule = TriggerRule(id="scene:focus", condition=ExternalMonitorConnected(), scene_id="focus")

    assert trigger_draft_from(rule).choice is TriggerChoice.EXTERNAL_MONITOR


def test_an_on_battery_rule_reads_back_as_its_choice() -> None:
    rule = TriggerRule(id="scene:focus", condition=OnBatteryPower(), scene_id="focus")

    assert trigger_draft_from(rule).choice is TriggerChoice.ON_BATTERY


def test_a_battery_threshold_rule_carries_its_percentage_back() -> None:
    rule = TriggerRule(id="scene:focus", condition=BatteryBelow(percent=15), scene_id="focus")

    draft = trigger_draft_from(rule)

    assert draft.choice is TriggerChoice.BATTERY_BELOW
    assert draft.percent == 15


def test_restore_on_exit_survives_the_round_trip() -> None:
    draft = TriggerDraft(choice=TriggerChoice.EXTERNAL_MONITOR, restore_on_exit=True)

    rule = rule_from(draft, "presentation")

    assert rule is not None
    assert trigger_draft_from(rule).restore_on_exit is True


@pytest.mark.parametrize(
    "choice",
    [TriggerChoice.EXTERNAL_MONITOR, TriggerChoice.ON_BATTERY, TriggerChoice.BATTERY_BELOW],
)
def test_every_choice_survives_a_round_trip(choice: TriggerChoice) -> None:
    draft = TriggerDraft(choice=choice, percent=25, restore_on_exit=True)

    rule = rule_from(draft, "focus")

    assert rule is not None
    restored = trigger_draft_from(rule)
    assert restored.choice is choice
    assert restored.restore_on_exit is True


def test_the_percentage_is_only_kept_for_the_threshold_choice() -> None:
    """Nothing else has anywhere to store it, so it returns to the default."""
    rule = rule_from(TriggerDraft(choice=TriggerChoice.ON_BATTERY, percent=25), "focus")

    assert rule is not None
    assert trigger_draft_from(rule).percent == DEFAULT_BATTERY_PERCENT


def test_the_rule_activates_the_scene_it_was_written_for() -> None:
    rule = rule_from(TriggerDraft(choice=TriggerChoice.ON_BATTERY), "power-saving")

    assert rule is not None
    assert rule.scene_id == "power-saving"


def test_the_rule_id_is_derived_from_the_scene() -> None:
    """Editing twice must replace the rule, not stack up one per save."""
    first = rule_from(TriggerDraft(choice=TriggerChoice.ON_BATTERY), "focus")
    second = rule_from(TriggerDraft(choice=TriggerChoice.EXTERNAL_MONITOR), "focus")

    assert first is not None and second is not None
    assert first.id == second.id == rule_id_for("focus")


def test_the_draft_cannot_be_changed_behind_with_toggle() -> None:
    """Frozen has to mean it: the dict was the one mutable way in."""
    draft = SceneDraft(name="Mia", toggles={SystemToggle.KEEP_AWAKE: True})

    assert not isinstance(draft.toggles, MutableMapping)
    assert draft.toggles == {SystemToggle.KEEP_AWAKE: True}


def test_the_draft_does_not_alias_the_dict_it_was_built_from() -> None:
    toggles = {SystemToggle.KEEP_AWAKE: True}
    draft = SceneDraft(name="Mia", toggles=toggles)

    toggles[SystemToggle.MICROPHONE_MUTED] = False

    assert SystemToggle.MICROPHONE_MUTED not in draft.toggles
