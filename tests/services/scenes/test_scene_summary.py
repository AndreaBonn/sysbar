from __future__ import annotations

import pytest

from sysbar.services.scenes.actions import SetOutputDevice, SetSetting, SetToggle, SystemToggle
from sysbar.services.scenes.apply import ActionOutcome, Status
from sysbar.services.scenes.models import PRESET_SCENES, Scene
from sysbar.services.scenes.summary import describe_scene, partial_note, trigger_announcement


def _preset(name: str) -> Scene:
    return next(scene for scene in PRESET_SCENES if scene.name == name)


def test_focus_reads_as_what_it_changes() -> None:
    assert describe_scene(_preset("Focus")) == (
        "Keep awake on · Do Not Disturb on · Microphone muted · +1 more"
    )


def test_power_saving_names_toggles_turned_off() -> None:
    assert describe_scene(_preset("Power saving")) == (
        "Keep awake off · Do Not Disturb off · Microphone on · +2 more"
    )


def test_an_output_device_is_named_by_the_device() -> None:
    scene = Scene(id="x", name="Desk", actions=(SetOutputDevice(device="hdmi-speakers"),))

    assert describe_scene(scene) == "Audio to hdmi-speakers"


def test_settings_only_scene_counts_them() -> None:
    scene = Scene(
        id="y",
        name="Quiet",
        actions=(SetSetting(key="alert-enabled", value=False),),
    )

    assert describe_scene(scene) == "+1 more"


def test_an_empty_scene_says_it_changes_nothing() -> None:
    assert describe_scene(Scene(id="z", name="Empty")) == "Changes nothing yet"


def test_a_single_toggle_has_no_counter() -> None:
    scene = Scene(
        id="w",
        name="Awake",
        actions=(SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=True),),
    )

    assert describe_scene(scene) == "Keep awake on"


def test_an_output_device_can_be_shown_by_its_readable_name() -> None:
    scene = Scene(id="x", name="Desk", actions=(SetOutputDevice(device="alsa_output.hdmi"),))

    text = describe_scene(scene, device_name={"alsa_output.hdmi": "HDMI speakers"}.get)

    assert text == "Audio to HDMI speakers"


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ([], ""),
        ([Status.APPLIED] * 3, ""),
        (
            [Status.APPLIED, Status.SKIPPED, Status.FAILED],
            "1 of 3 actions in Desk took effect.",
        ),
        ([Status.SKIPPED] * 3, "0 of 3 actions in Desk took effect."),
    ],
)
def test_partial_note_outcomes_report_only_incomplete_application(
    statuses: list[Status], expected: str
) -> None:
    action = SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=True)
    outcomes = [ActionOutcome(action=action, status=status) for status in statuses]

    assert partial_note(outcomes=outcomes, scene_name="Desk") == expected


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ([], "A trigger switched to Desk."),
        ([Status.APPLIED] * 3, "A trigger switched to Desk."),
        (
            [Status.APPLIED, Status.SKIPPED, Status.FAILED],
            "1 of 3 actions in Desk took effect.",
        ),
        ([Status.SKIPPED] * 3, "0 of 3 actions in Desk took effect."),
    ],
)
def test_trigger_announcement_outcomes_report_scene_and_application(
    statuses: list[Status], expected: str
) -> None:
    action = SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=True)
    outcomes = [ActionOutcome(action=action, status=status) for status in statuses]

    assert trigger_announcement(scene_name="Desk", outcomes=outcomes) == expected
