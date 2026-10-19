from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from sysbar.app.scenes_content import (
    TOGGLE_CHOICES,
    TRIGGER_CHOICES,
    FormValues,
    form_draft,
    trigger_rows_visibility,
)
from sysbar.services.scenes.actions import SetSetting, SystemToggle
from sysbar.services.scenes.editing import SceneDraft, TriggerChoice
from sysbar.services.scenes.models import PRESET_SCENES


def test_trigger_choices_order_and_labels_match_the_form() -> None:
    choices, labels = zip(*TRIGGER_CHOICES, strict=True)
    assert len(labels) == len(choices) == 4
    assert TRIGGER_CHOICES == (
        (TriggerChoice.NEVER, "Never"),
        (TriggerChoice.EXTERNAL_MONITOR, "An external monitor is connected"),
        (TriggerChoice.ON_BATTERY, "Running on battery"),
        (TriggerChoice.BATTERY_BELOW, "Battery drops below a level"),
    )


def test_toggle_choices_order_and_labels_match_the_form() -> None:
    choices, labels = zip(*TOGGLE_CHOICES, strict=True)
    assert len(labels) == len(choices) == 3
    assert TOGGLE_CHOICES == ((None, "Leave unchanged"), (True, "Turn on"), (False, "Turn off"))


@pytest.mark.parametrize(
    ("choice", "expected"),
    [
        (TriggerChoice.NEVER, (False, False)),
        (TriggerChoice.EXTERNAL_MONITOR, (False, True)),
        (TriggerChoice.ON_BATTERY, (False, True)),
        (TriggerChoice.BATTERY_BELOW, (True, True)),
    ],
)
def test_trigger_rows_visibility_each_choice_returns_expected_rows(
    choice: TriggerChoice, expected: tuple[bool, bool]
) -> None:
    assert trigger_rows_visibility(choice=choice) == expected


@pytest.mark.parametrize(
    ("name", "expected"), [("", "Focus"), ("   ", "Focus"), ("  Work  ", "Work")]
)
def test_form_draft_name_strips_or_uses_base(name: str, expected: str) -> None:
    values = FormValues(name=name, toggle_indices={}, device_index=0, device_names=("",))
    assert form_draft(values=values, base=PRESET_SCENES[0]).name == expected


def test_form_draft_toggle_indices_filter_unchanged_and_preserve_actions() -> None:
    values = FormValues(
        name="Work",
        toggle_indices={
            SystemToggle.KEEP_AWAKE: 0,
            SystemToggle.DO_NOT_DISTURB: 1,
            SystemToggle.MICROPHONE_MUTED: 2,
        },
        device_index=2,
        device_names=("", "speakers", "hdmi"),
    )
    assert form_draft(values=values, base=PRESET_SCENES[0]) == SceneDraft(
        name="Work",
        toggles={SystemToggle.DO_NOT_DISTURB: True, SystemToggle.MICROPHONE_MUTED: False},
        output_device="hdmi",
        preserved=(SetSetting(key="alert-enabled", value=False),),
    )
    assert values.toggle_indices[SystemToggle.KEEP_AWAKE] == 0


@pytest.mark.parametrize("index", [-1, 0, 3, 99])
def test_form_draft_invalid_or_neutral_device_returns_empty_name(index: int) -> None:
    base = PRESET_SCENES[0]
    valid = FormValues(name="Work", toggle_indices={}, device_index=1, device_names=("", "hdmi"))
    values = FormValues(
        name="Work", toggle_indices={}, device_index=index, device_names=("", "hdmi")
    )
    assert form_draft(values=valid, base=base).output_device == "hdmi"
    assert form_draft(values=values, base=base).output_device == ""


def test_form_draft_empty_device_names_returns_empty_name() -> None:
    values = FormValues(name="Work", toggle_indices={}, device_index=0, device_names=())
    assert form_draft(values=values, base=PRESET_SCENES[0]).output_device == ""


def test_form_values_frozen_rejects_name_changes() -> None:
    values = FormValues(name="Work", toggle_indices={}, device_index=0, device_names=("",))
    with pytest.raises(FrozenInstanceError):
        values.__setattr__("name", "Changed")
    assert values.name == "Work"
