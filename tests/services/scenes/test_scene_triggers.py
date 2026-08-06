"""When a trigger switches scene, and when it deliberately does not."""

from __future__ import annotations

import pytest

from sysbar.services.scenes.triggers import (
    BATTERY_HYSTERESIS_PERCENT,
    BatteryBelow,
    ExternalMonitorConnected,
    OnBatteryPower,
    Ownership,
    TriggerError,
    TriggerMemory,
    TriggerRule,
    TriggerState,
    condition_from_dict,
    evaluate,
)


def _rule(
    rule_id: str = "r1",
    condition: object = None,
    scene_id: str = "presentation",
    *,
    restore_on_exit: bool = False,
    enabled: bool = True,
) -> TriggerRule:
    return TriggerRule(
        id=rule_id,
        condition=condition or ExternalMonitorConnected(),  # type: ignore[arg-type]
        scene_id=scene_id,
        restore_on_exit=restore_on_exit,
        enabled=enabled,
    )


_DOCKED = TriggerState(external_monitor=True)
_UNDOCKED = TriggerState(external_monitor=False)


# --- invariants -----------------------------------------------------------


def test_a_rule_needs_an_id() -> None:
    with pytest.raises(TriggerError, match="needs an id"):
        _rule(rule_id="")


def test_a_rule_needs_a_scene() -> None:
    with pytest.raises(TriggerError, match="needs a scene"):
        _rule(scene_id="")


def test_a_battery_threshold_must_be_a_percentage() -> None:
    with pytest.raises(TriggerError, match="out of range"):
        BatteryBelow(percent=0)
    with pytest.raises(TriggerError, match="out of range"):
        BatteryBelow(percent=101)


# --- activation -----------------------------------------------------------


def test_a_satisfied_condition_activates_its_scene() -> None:
    decision = evaluate([_rule()], _DOCKED, TriggerMemory())

    assert decision.activate == "presentation"
    assert decision.owner == Ownership(rule_id="r1", scene_id="presentation")


def test_an_unsatisfied_condition_does_nothing() -> None:
    assert evaluate([_rule()], _UNDOCKED, TriggerMemory()).is_noop is True


def test_a_disabled_rule_never_fires() -> None:
    decision = evaluate([_rule(enabled=False)], _DOCKED, TriggerMemory())

    assert decision.is_noop is True


def test_the_same_state_delivered_again_produces_nothing() -> None:
    """Sources report state, so re-delivery must not re-activate."""
    first = evaluate([_rule()], _DOCKED, TriggerMemory())

    second = evaluate(
        [_rule()],
        _DOCKED,
        TriggerMemory(engaged=first.engaged, owner=first.owner, active_scene_id="presentation"),
    )

    assert second.is_noop is True


def test_the_first_matching_rule_wins() -> None:
    rules = [
        _rule("r1", ExternalMonitorConnected(), "presentation"),
        _rule("r2", ExternalMonitorConnected(), "focus"),
    ]

    assert evaluate(rules, _DOCKED, TriggerMemory()).activate == "presentation"


def test_an_empty_rule_list_does_nothing() -> None:
    assert evaluate([], _DOCKED, TriggerMemory()).is_noop is True


# --- never fighting the user ----------------------------------------------


def test_a_manually_chosen_scene_is_never_overwritten() -> None:
    memory = TriggerMemory(active_scene_id="focus", owner=None)

    decision = evaluate([_rule()], _DOCKED, memory)

    assert decision.is_noop is True


def test_a_trigger_can_still_fire_when_no_scene_is_active() -> None:
    memory = TriggerMemory(active_scene_id="", owner=None)

    assert evaluate([_rule()], _DOCKED, memory).activate == "presentation"


def test_a_scene_changed_by_hand_is_not_cleared_when_the_condition_lapses() -> None:
    memory = TriggerMemory(
        engaged=frozenset({"r1"}),
        owner=Ownership(rule_id="r1", scene_id="presentation"),
        active_scene_id="focus",
    )

    decision = evaluate([_rule(restore_on_exit=True)], _UNDOCKED, memory)

    assert decision.clear is False
    assert decision.owner is None


# --- release --------------------------------------------------------------


def test_leaving_the_condition_clears_when_the_rule_says_so() -> None:
    memory = TriggerMemory(
        engaged=frozenset({"r1"}),
        owner=Ownership(rule_id="r1", scene_id="presentation"),
        active_scene_id="presentation",
    )

    decision = evaluate([_rule(restore_on_exit=True)], _UNDOCKED, memory)

    assert decision.clear is True
    assert decision.owner is None


def test_leaving_the_condition_keeps_the_scene_when_the_rule_does_not_restore() -> None:
    memory = TriggerMemory(
        engaged=frozenset({"r1"}),
        owner=Ownership(rule_id="r1", scene_id="presentation"),
        active_scene_id="presentation",
    )

    decision = evaluate([_rule(restore_on_exit=False)], _UNDOCKED, memory)

    assert decision.clear is False
    assert decision.owner is None


def test_a_deleted_rule_releases_its_ownership_without_clearing() -> None:
    memory = TriggerMemory(
        engaged=frozenset({"gone"}),
        owner=Ownership(rule_id="gone", scene_id="presentation"),
        active_scene_id="presentation",
    )

    decision = evaluate([], _UNDOCKED, memory)

    assert decision.clear is False
    assert decision.owner is None


def test_releasing_twice_does_nothing_the_second_time() -> None:
    memory = TriggerMemory(
        engaged=frozenset({"r1"}),
        owner=Ownership(rule_id="r1", scene_id="presentation"),
        active_scene_id="presentation",
    )
    first = evaluate([_rule(restore_on_exit=True)], _UNDOCKED, memory)

    second = evaluate(
        [_rule(restore_on_exit=True)],
        _UNDOCKED,
        TriggerMemory(engaged=first.engaged, owner=first.owner, active_scene_id=""),
    )

    assert second.is_noop is True


# --- hysteresis -----------------------------------------------------------


def _battery(percent: float) -> TriggerState:
    return TriggerState(on_battery=True, battery_percent=percent)


def test_a_battery_rule_fires_at_the_threshold() -> None:
    rule = _rule(condition=BatteryBelow(percent=20), scene_id="power-saving")

    assert evaluate([rule], _battery(20), TriggerMemory()).activate == "power-saving"


def test_a_battery_rule_does_not_fire_above_the_threshold() -> None:
    rule = _rule(condition=BatteryBelow(percent=20), scene_id="power-saving")

    assert evaluate([rule], _battery(21), TriggerMemory()).is_noop is True


def test_an_engaged_battery_rule_holds_just_above_the_threshold() -> None:
    """Hysteresis: the value must climb clear of the line before letting go."""
    rule = _rule(condition=BatteryBelow(percent=20), scene_id="power-saving", restore_on_exit=True)
    memory = TriggerMemory(
        engaged=frozenset({"r1"}),
        owner=Ownership(rule_id="r1", scene_id="power-saving"),
        active_scene_id="power-saving",
    )

    decision = evaluate([rule], _battery(22), memory)

    assert decision.clear is False
    assert "r1" in decision.engaged


def test_an_engaged_battery_rule_lets_go_past_the_hysteresis_band() -> None:
    rule = _rule(condition=BatteryBelow(percent=20), scene_id="power-saving", restore_on_exit=True)
    memory = TriggerMemory(
        engaged=frozenset({"r1"}),
        owner=Ownership(rule_id="r1", scene_id="power-saving"),
        active_scene_id="power-saving",
    )

    decision = evaluate([rule], _battery(20 + BATTERY_HYSTERESIS_PERCENT), memory)

    assert decision.clear is True


def test_a_battery_rule_never_fires_without_a_reading() -> None:
    rule = _rule(condition=BatteryBelow(percent=20), scene_id="power-saving")

    assert evaluate([rule], TriggerState(on_battery=True), TriggerMemory()).is_noop is True


def test_hovering_at_the_threshold_does_not_flap() -> None:
    """The scenario hysteresis exists for: many samples, one activation."""
    rule = _rule(condition=BatteryBelow(percent=20), scene_id="power-saving", restore_on_exit=True)
    memory = TriggerMemory()
    commands: list[str] = []

    for percent in (21, 20, 21, 20, 22, 19, 21):
        decision = evaluate([rule], _battery(percent), memory)
        if decision.activate:
            commands.append(f"activate:{decision.activate}")
        if decision.clear:
            commands.append("clear")
        memory = TriggerMemory(
            engaged=decision.engaged,
            owner=decision.owner,
            active_scene_id=decision.activate or memory.active_scene_id,
        )

    assert commands == ["activate:power-saving"]


# --- power source ---------------------------------------------------------


def test_an_on_battery_rule_fires_when_unplugged() -> None:
    rule = _rule(condition=OnBatteryPower(), scene_id="power-saving")

    assert evaluate([rule], TriggerState(on_battery=True), TriggerMemory()).activate


def test_an_on_battery_rule_does_not_fire_on_mains() -> None:
    rule = _rule(condition=OnBatteryPower(), scene_id="power-saving")

    assert evaluate([rule], TriggerState(on_battery=False), TriggerMemory()).is_noop is True


# --- stored form ----------------------------------------------------------


@pytest.mark.parametrize(
    "condition",
    [ExternalMonitorConnected(), OnBatteryPower(), BatteryBelow(percent=15)],
)
def test_a_condition_survives_a_round_trip(condition: object) -> None:
    assert condition_from_dict(condition.to_dict()) == condition  # type: ignore[attr-defined]


def test_a_rule_survives_a_round_trip() -> None:
    rule = _rule(condition=BatteryBelow(percent=15), restore_on_exit=True)

    assert TriggerRule.from_dict(rule.to_dict()) == rule


def test_an_unknown_condition_is_refused() -> None:
    with pytest.raises(TriggerError, match="unknown trigger condition"):
        condition_from_dict({"kind": "moon-phase"})


def test_a_battery_condition_without_a_number_is_refused() -> None:
    with pytest.raises(TriggerError, match="not a number"):
        condition_from_dict({"kind": "battery-below", "percent": "twenty"})


def test_a_rule_without_a_condition_is_refused() -> None:
    with pytest.raises(TriggerError, match="condition is missing"):
        TriggerRule.from_dict({"id": "r1", "scene_id": "focus"})
