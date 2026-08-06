"""The typed scene actions and their round trip through stored data."""

from __future__ import annotations

import pytest

from sysbar.services.scenes.actions import (
    SceneActionError,
    SetOutputDevice,
    SetSetting,
    SetToggle,
    SystemToggle,
    action_from_dict,
    action_to_dict,
)

# --- construction ---------------------------------------------------------


def test_a_toggle_action_carries_its_target_state() -> None:
    action = SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=True)

    assert action.toggle is SystemToggle.KEEP_AWAKE
    assert action.value is True


def test_a_setting_action_accepts_a_whitelisted_key() -> None:
    assert SetSetting(key="alert-enabled", value=False).key == "alert-enabled"


def test_a_setting_action_refuses_a_key_outside_the_whitelist() -> None:
    with pytest.raises(SceneActionError, match="not writable"):
        SetSetting(key="app-language", value="it")


def test_an_output_device_action_needs_a_device() -> None:
    with pytest.raises(SceneActionError, match="device name"):
        SetOutputDevice(device="")


# --- round trip -----------------------------------------------------------


@pytest.mark.parametrize(
    "action",
    [
        SetToggle(toggle=SystemToggle.DO_NOT_DISTURB, value=True),
        SetToggle(toggle=SystemToggle.MICROPHONE_MUTED, value=False),
        SetSetting(key="monitor-interval-seconds", value=5),
        SetSetting(key="alert-enabled", value=True),
        SetOutputDevice(device="alsa_output.hdmi"),
    ],
)
def test_an_action_survives_a_round_trip(action: object) -> None:
    restored = action_from_dict(action_to_dict(action))  # type: ignore[arg-type]

    assert restored == action


def test_the_stored_form_records_the_kind() -> None:
    stored = action_to_dict(SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=True))

    assert stored["kind"] == "toggle"


# --- corrupt data ---------------------------------------------------------


def test_an_unknown_kind_is_refused() -> None:
    with pytest.raises(SceneActionError, match="unknown action kind"):
        action_from_dict({"kind": "launch-rocket"})


def test_a_missing_kind_is_refused() -> None:
    with pytest.raises(SceneActionError, match="unknown action kind"):
        action_from_dict({"toggle": "keep-awake"})


def test_an_unknown_toggle_is_refused() -> None:
    with pytest.raises(SceneActionError, match="unknown toggle"):
        action_from_dict({"kind": "toggle", "toggle": "self-destruct", "value": True})


def test_a_setting_without_a_value_is_refused() -> None:
    with pytest.raises(SceneActionError, match="missing key or value"):
        action_from_dict({"kind": "setting", "key": "alert-enabled"})


def test_a_setting_with_an_unsupported_value_type_is_refused() -> None:
    with pytest.raises(SceneActionError, match="unsupported setting value"):
        action_from_dict({"kind": "setting", "key": "alert-enabled", "value": [1, 2]})


def test_a_stored_setting_outside_the_whitelist_is_refused() -> None:
    """The whitelist holds on the way in too, not just in the editor."""
    with pytest.raises(SceneActionError, match="not writable"):
        action_from_dict({"kind": "setting", "key": "app-language", "value": "it"})


def test_an_output_device_without_a_device_is_refused() -> None:
    with pytest.raises(SceneActionError, match="missing device"):
        action_from_dict({"kind": "output-device"})


def test_a_stored_empty_device_is_refused() -> None:
    with pytest.raises(SceneActionError, match="device name"):
        action_from_dict({"kind": "output-device", "device": ""})


def test_a_toggle_defaults_to_off_when_the_value_is_absent() -> None:
    action = action_from_dict({"kind": "toggle", "toggle": "keep-awake"})

    assert action == SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=False)
