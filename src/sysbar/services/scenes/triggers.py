"""Deciding when an event should switch scene, and when it should stop.

The hard part is not detecting the event, it is not fighting the user. Four
rules, in order of how much trouble they save:

* **Never overwrite a manual choice.** If a scene is active and no trigger put
  it there, no trigger takes it away. Someone who picked Focus by hand does not
  want a monitor being plugged in to undo it.
* **Ownership, not history.** The rule that activates marks the scene as its
  own. When its condition lapses it clears the scene only if that scene is still
  the one it set. No stack of previous states to unwind, which falls apart the
  moment two rules overlap or the user intervenes in the middle.
* **State, not edges.** Sources report what is true now; the engine works out
  the transition. Re-delivering the same state produces no command, so
  idempotence is structural rather than something every source must remember.
* **Hysteresis on thresholds.** A battery hovering at the limit would otherwise
  activate and clear repeatedly. Entering and leaving use different values.

Restoring on exit is opt-in per rule. "Plug in the monitor, get Presentation"
usually wants the scene to end when the monitor goes; "battery got low, go into
power saving" usually does not want it undone the moment it charges past the
line.

Pure: no clock, no I/O. The adapters that read the display and the battery live
elsewhere, and this evaluates what they report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Literal

# How far a value must climb back before a threshold rule lets go. Without it a
# battery sitting at the limit toggles the scene on every sample.
BATTERY_HYSTERESIS_PERCENT: Final = 5.0

KIND_EXTERNAL_MONITOR: Final = "external-monitor"
KIND_BATTERY_BELOW: Final = "battery-below"
KIND_ON_BATTERY: Final = "on-battery"


class TriggerError(ValueError):
    """Raised when stored trigger data cannot be read back."""


@dataclass(frozen=True)
class ExternalMonitorConnected:
    """Satisfied while a display other than the built-in one is attached."""

    kind: Literal["external-monitor"] = KIND_EXTERNAL_MONITOR

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind}


@dataclass(frozen=True)
class BatteryBelow:
    """Satisfied while the charge is at or under ``percent``."""

    percent: float
    kind: Literal["battery-below"] = KIND_BATTERY_BELOW

    def __post_init__(self) -> None:
        if not 0 < self.percent <= 100:
            raise TriggerError(f"battery threshold out of range: {self.percent}")

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "percent": self.percent}


@dataclass(frozen=True)
class OnBatteryPower:
    """Satisfied while the machine is running from its battery."""

    kind: Literal["on-battery"] = KIND_ON_BATTERY

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind}


TriggerCondition = ExternalMonitorConnected | BatteryBelow | OnBatteryPower


@dataclass(frozen=True)
class TriggerRule:
    """One condition, the scene it activates, and whether leaving undoes it."""

    id: str
    condition: TriggerCondition
    scene_id: str
    restore_on_exit: bool = False
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.id:
            raise TriggerError("a trigger needs an id")
        if not self.scene_id:
            raise TriggerError("a trigger needs a scene to activate")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "condition": self.condition.to_dict(),
            "scene_id": self.scene_id,
            "restore_on_exit": self.restore_on_exit,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TriggerRule:
        condition = data.get("condition")
        if not isinstance(condition, dict):
            raise TriggerError("trigger condition is missing or malformed")
        return cls(
            id=str(data.get("id", "")),
            condition=condition_from_dict(condition),
            scene_id=str(data.get("scene_id", "")),
            restore_on_exit=bool(data.get("restore_on_exit", False)),
            enabled=bool(data.get("enabled", True)),
        )


def condition_from_dict(data: dict[str, object]) -> TriggerCondition:
    """Rebuild a condition, raising on an unknown kind or a bad payload."""
    kind = str(data.get("kind", ""))
    match kind:
        case "external-monitor":
            return ExternalMonitorConnected()
        case "on-battery":
            return OnBatteryPower()
        case "battery-below":
            percent = data.get("percent")
            if not isinstance(percent, int | float):
                raise TriggerError(f"battery threshold is not a number: {percent!r}")
            return BatteryBelow(percent=float(percent))
        case _:
            raise TriggerError(f"unknown trigger condition: {kind!r}")


@dataclass(frozen=True)
class TriggerState:
    """What the sources currently report."""

    external_monitor: bool = False
    on_battery: bool = False
    battery_percent: float | None = None


@dataclass(frozen=True)
class Ownership:
    """The rule that put the active scene there."""

    rule_id: str
    scene_id: str


@dataclass(frozen=True)
class Decision:
    """What to do about this state, and what to remember for the next one."""

    activate: str | None = None
    clear: bool = False
    owner: Ownership | None = None
    engaged: frozenset[str] = field(default_factory=frozenset)

    @property
    def is_noop(self) -> bool:
        return self.activate is None and not self.clear


def is_satisfied(condition: TriggerCondition, state: TriggerState, *, engaged: bool) -> bool:
    """Whether ``condition`` holds, given whether it already held.

    ``engaged`` is what makes hysteresis possible: a threshold that has already
    fired needs the value to climb further back before it lets go.
    """
    match condition:
        case ExternalMonitorConnected():
            return state.external_monitor
        case OnBatteryPower():
            return state.on_battery
        case BatteryBelow(percent=percent):
            return _battery_below(state, percent, engaged=engaged)


def _battery_below(state: TriggerState, percent: float, *, engaged: bool) -> bool:
    value = state.battery_percent
    if value is None:
        return False
    if engaged:
        return value < percent + BATTERY_HYSTERESIS_PERCENT
    return value <= percent


@dataclass(frozen=True)
class TriggerMemory:
    """What the previous evaluation left behind."""

    engaged: frozenset[str] = field(default_factory=frozenset)
    owner: Ownership | None = None
    #: The scene the user currently has active, whoever set it.
    active_scene_id: str = ""


def evaluate(rules: list[TriggerRule], state: TriggerState, memory: TriggerMemory) -> Decision:
    """Decide what this state means, given what the last one did.

    The first enabled rule whose condition holds wins; the list is the priority,
    which is deterministic and needs no separate ordering to explain.
    """
    engaged = frozenset(
        rule.id
        for rule in rules
        if rule.enabled and is_satisfied(rule.condition, state, engaged=rule.id in memory.engaged)
    )
    winner = next((rule for rule in rules if rule.id in engaged), None)
    if winner is None:
        return _decide_release(rules, memory, engaged)
    return _decide_activation(winner, memory, engaged)


def _decide_activation(
    winner: TriggerRule, memory: TriggerMemory, engaged: frozenset[str]
) -> Decision:
    already_ours = memory.owner is not None and memory.owner.rule_id == winner.id
    manual_scene = memory.active_scene_id and memory.owner is None
    if already_ours or manual_scene:
        return Decision(owner=memory.owner, engaged=engaged)
    owner = Ownership(rule_id=winner.id, scene_id=winner.scene_id)
    return Decision(activate=winner.scene_id, owner=owner, engaged=engaged)


def _decide_release(
    rules: list[TriggerRule], memory: TriggerMemory, engaged: frozenset[str]
) -> Decision:
    owner = memory.owner
    if owner is None:
        return Decision(engaged=engaged)
    rule = next((candidate for candidate in rules if candidate.id == owner.rule_id), None)
    changed_by_hand = memory.active_scene_id != owner.scene_id
    if rule is None or not rule.restore_on_exit or changed_by_hand:
        # Ownership ends either way: the scene is no longer ours to clear.
        return Decision(owner=None, engaged=engaged)
    return Decision(clear=True, owner=None, engaged=engaged)
