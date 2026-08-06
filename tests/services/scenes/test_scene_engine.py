"""Driving scene changes from reported state, at most one per interval."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from sysbar.services.scenes.apply import ScenePorts
from sysbar.services.scenes.constants import TRIGGER_MIN_INTERVAL_SECONDS
from sysbar.services.scenes.engine import TriggerActions, TriggerEngine
from sysbar.services.scenes.models import Scene, SceneOrigin
from sysbar.services.scenes.service import SceneService
from sysbar.services.scenes.triggers import (
    ExternalMonitorConnected,
    OnBatteryPower,
    TriggerRule,
    TriggerState,
)


@dataclass
class _Recorder:
    activated: list[str] = field(default_factory=list)
    cleared: int = 0
    announced: list[str] = field(default_factory=list)

    def actions(self) -> TriggerActions:
        return TriggerActions(
            activate=self.activated.append,
            clear=self._clear,
            announce=self.announced.append,
        )

    def _clear(self) -> None:
        self.cleared += 1


class _Clock:
    """A clock the test advances by hand."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _rule(
    rule_id: str = "r1", scene_id: str = "presentation", *, restore_on_exit: bool = True
) -> TriggerRule:
    return TriggerRule(
        id=rule_id,
        condition=ExternalMonitorConnected(),
        scene_id=scene_id,
        restore_on_exit=restore_on_exit,
    )


@pytest.fixture
def recorder() -> _Recorder:
    return _Recorder()


@pytest.fixture
def clock() -> _Clock:
    return _Clock()


def _engine(
    recorder: _Recorder, clock: _Clock, rules: list[TriggerRule] | None = None
) -> TriggerEngine:
    return TriggerEngine(lambda: rules or [_rule()], recorder.actions(), clock)


_DOCKED = TriggerState(external_monitor=True)
_UNDOCKED = TriggerState(external_monitor=False)


# --- activation -----------------------------------------------------------


def test_a_satisfied_condition_activates_the_scene(recorder: _Recorder, clock: _Clock) -> None:
    _engine(recorder, clock).update(_DOCKED)

    assert recorder.activated == ["presentation"]


def test_activating_announces_it(recorder: _Recorder, clock: _Clock) -> None:
    _engine(recorder, clock).update(_DOCKED)

    assert recorder.announced == ["presentation"]


def test_an_unsatisfied_condition_does_nothing(recorder: _Recorder, clock: _Clock) -> None:
    _engine(recorder, clock).update(_UNDOCKED)

    assert recorder.activated == []


def test_the_same_state_twice_activates_once(recorder: _Recorder, clock: _Clock) -> None:
    engine = _engine(recorder, clock)

    engine.update(_DOCKED)
    clock.advance(TRIGGER_MIN_INTERVAL_SECONDS * 2)
    engine.update(_DOCKED)

    assert recorder.activated == ["presentation"]


def test_the_engine_reports_which_scene_it_owns(recorder: _Recorder, clock: _Clock) -> None:
    engine = _engine(recorder, clock)

    engine.update(_DOCKED)

    assert engine.owned_scene == "presentation"


def test_nothing_is_owned_before_a_trigger_fires(recorder: _Recorder, clock: _Clock) -> None:
    assert _engine(recorder, clock).owned_scene is None


# --- release --------------------------------------------------------------


def test_leaving_the_condition_clears_when_the_rule_restores(
    recorder: _Recorder, clock: _Clock
) -> None:
    engine = _engine(recorder, clock)
    engine.update(_DOCKED)
    clock.advance(TRIGGER_MIN_INTERVAL_SECONDS * 2)

    engine.update(_UNDOCKED)

    assert recorder.cleared == 1


def test_leaving_the_condition_keeps_the_scene_when_the_rule_does_not_restore(
    recorder: _Recorder, clock: _Clock
) -> None:
    engine = _engine(recorder, clock, [_rule(restore_on_exit=False)])
    engine.update(_DOCKED)
    clock.advance(TRIGGER_MIN_INTERVAL_SECONDS * 2)

    engine.update(_UNDOCKED)

    assert recorder.cleared == 0


def test_ownership_ends_after_a_release(recorder: _Recorder, clock: _Clock) -> None:
    engine = _engine(recorder, clock)
    engine.update(_DOCKED)
    clock.advance(TRIGGER_MIN_INTERVAL_SECONDS * 2)

    engine.update(_UNDOCKED)

    assert engine.owned_scene is None


# --- not fighting the user ------------------------------------------------


def test_a_scene_chosen_by_hand_is_not_overwritten(recorder: _Recorder, clock: _Clock) -> None:
    engine = _engine(recorder, clock)
    engine.note_active_scene("focus")

    engine.update(_DOCKED)

    assert recorder.activated == []


def test_a_scene_changed_by_hand_afterwards_is_not_cleared(
    recorder: _Recorder, clock: _Clock
) -> None:
    engine = _engine(recorder, clock)
    engine.update(_DOCKED)
    clock.advance(TRIGGER_MIN_INTERVAL_SECONDS * 2)
    engine.note_active_scene("focus")

    engine.update(_UNDOCKED)

    assert recorder.cleared == 0


# --- rate limit -----------------------------------------------------------


def test_two_activations_inside_the_interval_are_cut_to_one(
    recorder: _Recorder, clock: _Clock
) -> None:
    rules = [_rule("r1", "presentation"), _rule("r2", "focus")]
    engine = TriggerEngine(lambda: rules, recorder.actions(), clock)
    engine.update(_DOCKED)

    engine.note_active_scene("")
    rules.pop(0)
    engine.update(_DOCKED)

    assert recorder.activated == ["presentation"]


def test_an_activation_after_the_interval_goes_through(recorder: _Recorder, clock: _Clock) -> None:
    rules = [_rule("r1", "presentation")]
    engine = TriggerEngine(lambda: rules, recorder.actions(), clock)
    engine.update(_DOCKED)
    clock.advance(TRIGGER_MIN_INTERVAL_SECONDS)

    engine.note_active_scene("")
    rules[:] = [_rule("r2", "focus")]
    engine.update(_DOCKED)

    assert recorder.activated == ["presentation", "focus"]


def test_the_first_activation_is_never_rate_limited(recorder: _Recorder, clock: _Clock) -> None:
    _engine(recorder, clock).update(_DOCKED)

    assert recorder.activated == ["presentation"]


# --- rules read afresh ----------------------------------------------------


def test_rules_are_read_on_every_update(recorder: _Recorder, clock: _Clock) -> None:
    """A rule added while the engine runs takes effect without a restart."""
    rules: list[TriggerRule] = []
    engine = TriggerEngine(lambda: rules, recorder.actions(), clock)
    engine.update(TriggerState(on_battery=True))

    rules.append(TriggerRule(id="r1", condition=OnBatteryPower(), scene_id="power-saving"))
    engine.update(TriggerState(on_battery=True))

    assert recorder.activated == ["power-saving"]


# --- wiring: the engine follows the service, whoever changed the scene -----


@dataclass
class _FakePorts:
    """Minimal ports: this suite cares about who owns a scene, not what it does."""

    written: dict[str, object] = field(default_factory=dict)

    def supports(self, toggle: object) -> bool:
        return True

    def set_keep_awake(self, on: bool) -> None: ...
    def set_do_not_disturb(self, on: bool) -> None: ...
    def set_microphone_muted(self, on: bool) -> None: ...

    def set(self, key: str, value: object) -> None:
        self.written[key] = value

    def set_output_device(self, device: str) -> bool:
        return True

    def ports(self) -> ScenePorts:
        return ScenePorts(toggles=self, settings=self, audio=self)


def _wired(rules: list[TriggerRule], clock: _Clock) -> tuple[SceneService, TriggerEngine]:
    """Service and engine cabled the way ScenesFeature cables them.

    The engine learns the active scene from the service's ``changed`` signal
    rather than from every caller remembering to tell it, because a caller that
    forgets makes a trigger overwrite a scene the user chose by hand.
    """
    service = SceneService(
        _FakePorts().ports(),
        scenes=[
            Scene(id="focus", name="Focus", origin=SceneOrigin.BUILT_IN),
            Scene(id="presentazione", name="Presentazione", origin=SceneOrigin.USER),
        ],
        active_id="",
    )
    engine = TriggerEngine(
        lambda: rules,
        TriggerActions(
            activate=service.activate,
            clear=service.clear,
            announce=lambda _scene_id: None,
        ),
        clock,
    )
    service.connect("changed", lambda _service: engine.note_active_scene(service.active_id))
    return service, engine


def test_a_scene_activated_straight_on_the_service_counts_as_manual(clock: _Clock) -> None:
    """No trigger may overwrite a scene the user chose, by whichever route."""
    rules = [_rule("monitor", "presentazione")]
    service, engine = _wired(rules, clock)

    service.activate("focus")
    engine.update(TriggerState(external_monitor=True))

    assert service.active_id == "focus"


def test_a_manual_scene_set_mid_ownership_is_not_cleared_on_release(clock: _Clock) -> None:
    rules = [_rule("monitor", "presentazione", restore_on_exit=True)]
    service, engine = _wired(rules, clock)

    engine.update(TriggerState(external_monitor=True))
    assert service.active_id == "presentazione"
    service.activate("focus")
    clock.advance(TRIGGER_MIN_INTERVAL_SECONDS)
    engine.update(TriggerState(external_monitor=False))

    assert service.active_id == "focus"
