"""Applying a scene's actions, including when the system cannot honour one."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from sysbar.services.scenes.actions import (
    SceneAction,
    SetOutputDevice,
    SetSetting,
    SetToggle,
    SystemToggle,
)
from sysbar.services.scenes.apply import (
    ScenePorts,
    Status,
    applied_count,
    apply_action,
    apply_actions,
)


@dataclass
class _FakeToggles:
    supported: set[SystemToggle] = field(default_factory=lambda: set(SystemToggle))
    calls: list[str] = field(default_factory=list)

    def supports(self, toggle: SystemToggle) -> bool:
        return toggle in self.supported

    def set_keep_awake(self, on: bool) -> None:
        self.calls.append(f"keep-awake:{on}")

    def set_do_not_disturb(self, on: bool) -> None:
        self.calls.append(f"dnd:{on}")

    def set_microphone_muted(self, on: bool) -> None:
        self.calls.append(f"mic:{on}")


@dataclass
class _FakeSettings:
    written: list[tuple[str, object]] = field(default_factory=list)
    fail: bool = False

    def set(self, key: str, value: object) -> None:
        if self.fail:
            raise RuntimeError("settings backend is gone")
        self.written.append((key, value))


@dataclass
class _FakeAudio:
    available: set[str] = field(default_factory=set)
    selected: list[str] = field(default_factory=list)

    def set_output_device(self, device: str) -> bool:
        if device not in self.available:
            return False
        self.selected.append(device)
        return True


def _ports(
    toggles: _FakeToggles | None = None,
    settings: _FakeSettings | None = None,
    audio: _FakeAudio | None = None,
) -> ScenePorts:
    return ScenePorts(
        toggles=toggles or _FakeToggles(),
        settings=settings or _FakeSettings(),
        audio=audio or _FakeAudio(),
    )


# --- toggles --------------------------------------------------------------


@pytest.mark.parametrize(
    ("toggle", "expected"),
    [
        (SystemToggle.KEEP_AWAKE, "keep-awake:True"),
        (SystemToggle.DO_NOT_DISTURB, "dnd:True"),
        (SystemToggle.MICROPHONE_MUTED, "mic:True"),
    ],
)
def test_each_toggle_reaches_its_own_setter(toggle: SystemToggle, expected: str) -> None:
    toggles = _FakeToggles()

    outcome = apply_action(SetToggle(toggle=toggle, value=True), _ports(toggles=toggles))

    assert outcome.status is Status.APPLIED
    assert toggles.calls == [expected]


def test_a_toggle_can_be_driven_off() -> None:
    toggles = _FakeToggles()

    apply_action(SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=False), _ports(toggles=toggles))

    assert toggles.calls == ["keep-awake:False"]


def test_an_unsupported_toggle_is_skipped_not_failed() -> None:
    toggles = _FakeToggles(supported=set())

    outcome = apply_action(
        SetToggle(toggle=SystemToggle.MICROPHONE_MUTED, value=True), _ports(toggles=toggles)
    )

    assert outcome.status is Status.SKIPPED
    assert toggles.calls == []


def test_a_skipped_toggle_says_why() -> None:
    toggles = _FakeToggles(supported=set())

    outcome = apply_action(
        SetToggle(toggle=SystemToggle.MICROPHONE_MUTED, value=True), _ports(toggles=toggles)
    )

    assert "microphone-muted" in outcome.reason


# --- settings -------------------------------------------------------------


def test_a_setting_is_written() -> None:
    settings = _FakeSettings()

    outcome = apply_action(SetSetting(key="alert-enabled", value=False), _ports(settings=settings))

    assert outcome.status is Status.APPLIED
    assert settings.written == [("alert-enabled", False)]


def test_a_settings_backend_error_is_reported_as_failed() -> None:
    settings = _FakeSettings(fail=True)

    outcome = apply_action(SetSetting(key="alert-enabled", value=False), _ports(settings=settings))

    assert outcome.status is Status.FAILED
    assert outcome.reason


# --- audio ----------------------------------------------------------------


def test_a_connected_output_device_is_selected() -> None:
    audio = _FakeAudio(available={"hdmi"})

    outcome = apply_action(SetOutputDevice(device="hdmi"), _ports(audio=audio))

    assert outcome.status is Status.APPLIED
    assert audio.selected == ["hdmi"]


def test_a_missing_output_device_is_skipped() -> None:
    audio = _FakeAudio(available=set())

    outcome = apply_action(SetOutputDevice(device="hdmi"), _ports(audio=audio))

    assert outcome.status is Status.SKIPPED
    assert "hdmi" in outcome.reason


# --- whole scenes ---------------------------------------------------------


def test_one_unavailable_action_does_not_stop_the_others() -> None:
    toggles = _FakeToggles()
    settings = _FakeSettings()
    actions: list[SceneAction] = [
        SetOutputDevice(device="missing"),
        SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=True),
        SetSetting(key="alert-enabled", value=False),
    ]

    outcomes = apply_actions(actions, _ports(toggles=toggles, settings=settings))

    assert [outcome.status for outcome in outcomes] == [
        Status.SKIPPED,
        Status.APPLIED,
        Status.APPLIED,
    ]


def test_the_applied_count_reports_how_much_of_the_scene_took_effect() -> None:
    actions: list[SceneAction] = [
        SetOutputDevice(device="missing"),
        SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=True),
    ]

    outcomes = apply_actions(actions, _ports())

    assert applied_count(outcomes) == 1
    assert len(outcomes) == 2


def test_an_empty_scene_applies_nothing_and_reports_nothing() -> None:
    assert apply_actions([], _ports()) == []
