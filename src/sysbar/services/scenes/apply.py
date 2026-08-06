"""Carrying out a scene's actions, reporting what each one did.

An action whose capability is missing is not an error. Choosing an audio output
on a machine with no audio backend is a scene doing less than it says, which the
user should be told about, not a failure that should abort the rest. So applying
returns an outcome per action and the caller can report "3 of 5 applied" rather
than either lying or stopping.

The ports are grouped by capability rather than one method per action: with a
method per action they would grow every time the union does, and every fake in
every test would have to grow with them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .actions import SceneAction, SetOutputDevice, SetSetting, SetToggle, SystemToggle

log = logging.getLogger(__name__)


class Status(StrEnum):
    """How one action ended."""

    APPLIED = "applied"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class ActionOutcome:
    """The result of applying one action."""

    action: SceneAction
    status: Status
    reason: str = ""

    @property
    def is_applied(self) -> bool:
        return self.status is Status.APPLIED


class ToggleActions(Protocol):
    """Driving the system toggles a scene can set."""

    def set_keep_awake(self, on: bool) -> None: ...
    def set_do_not_disturb(self, on: bool) -> None: ...
    def set_microphone_muted(self, on: bool) -> None: ...
    def supports(self, toggle: SystemToggle) -> bool: ...


class SettingsActions(Protocol):
    """Writing a settings key."""

    def set(self, key: str, value: object) -> None: ...


class AudioActions(Protocol):
    """Choosing the default audio output."""

    def set_output_device(self, device: str) -> bool: ...


@dataclass(frozen=True)
class ScenePorts:
    """Everything applying a scene needs, in one value."""

    toggles: ToggleActions
    settings: SettingsActions
    audio: AudioActions


def apply_action(action: SceneAction, ports: ScenePorts) -> ActionOutcome:
    """Carry out one action, reporting whether it took effect."""
    match action:
        case SetToggle():
            return _apply_toggle(action, ports.toggles)
        case SetSetting():
            return _apply_setting(action, ports.settings)
        case SetOutputDevice():
            return _apply_output_device(action, ports.audio)


def apply_actions(actions: list[SceneAction], ports: ScenePorts) -> list[ActionOutcome]:
    """Carry out every action, never stopping at the first one that cannot run."""
    return [apply_action(action, ports) for action in actions]


def applied_count(outcomes: list[ActionOutcome]) -> int:
    return sum(1 for outcome in outcomes if outcome.is_applied)


def _apply_toggle(action: SetToggle, toggles: ToggleActions) -> ActionOutcome:
    if not toggles.supports(action.toggle):
        return ActionOutcome(action, Status.SKIPPED, f"{action.toggle.value} is not available")
    match action.toggle:
        case SystemToggle.KEEP_AWAKE:
            toggles.set_keep_awake(action.value)
        case SystemToggle.DO_NOT_DISTURB:
            toggles.set_do_not_disturb(action.value)
        case SystemToggle.MICROPHONE_MUTED:
            toggles.set_microphone_muted(action.value)
    return ActionOutcome(action, Status.APPLIED)


def _apply_setting(action: SetSetting, settings: SettingsActions) -> ActionOutcome:
    try:
        settings.set(action.key, action.value)
    except Exception as error:
        log.warning(
            "scene could not write a setting",
            extra={"key": action.key, "error": str(error)},
        )
        return ActionOutcome(action, Status.FAILED, str(error))
    return ActionOutcome(action, Status.APPLIED)


def _apply_output_device(action: SetOutputDevice, audio: AudioActions) -> ActionOutcome:
    if audio.set_output_device(action.device):
        return ActionOutcome(action, Status.APPLIED)
    return ActionOutcome(action, Status.SKIPPED, f"{action.device} is not connected")
