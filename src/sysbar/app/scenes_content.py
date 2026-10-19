"""Decide scene form choices and drafts independently of GTK widgets.

The editor builds widgets and saves scenes; choice ordering, row visibility and
form interpretation live here so they can be checked without a display.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..services.scenes.actions import SystemToggle
from ..services.scenes.editing import SceneDraft, TriggerChoice, draft_from
from ..services.scenes.models import Scene

_FIRST_DEVICE_INDEX = 0
_UNCHANGED_DEVICE = ""

# Combo order for the trigger condition; the index maps into this tuple.
TRIGGER_CHOICES: tuple[tuple[TriggerChoice, str], ...] = (
    (TriggerChoice.NEVER, "Never"),
    (TriggerChoice.EXTERNAL_MONITOR, "An external monitor is connected"),
    (TriggerChoice.ON_BATTERY, "Running on battery"),
    (TriggerChoice.BATTERY_BELOW, "Battery drops below a level"),
)

# Combo order for a toggle: leave alone, turn on, turn off.
TOGGLE_CHOICES: tuple[tuple[bool | None, str], ...] = (
    (None, "Leave unchanged"),
    (True, "Turn on"),
    (False, "Turn off"),
)


@dataclass(frozen=True)
class FormValues:
    """Widget values needed to interpret a scene form without GTK."""

    name: str
    toggle_indices: Mapping[SystemToggle, int]
    device_index: int
    device_names: tuple[str, ...]


def trigger_rows_visibility(choice: TriggerChoice) -> tuple[bool, bool]:
    """Only the threshold condition has a percentage to ask about."""
    return choice is TriggerChoice.BATTERY_BELOW, choice is not TriggerChoice.NEVER


def form_draft(values: FormValues, base: Scene) -> SceneDraft:
    """Interpret the form while retaining actions it cannot render.

    Parameters
    ----------
    values : FormValues
        Name and selections read from the editor widgets.
    base : Scene
        Original scene supplying the fallback name and unrendered actions.

    Returns
    -------
    SceneDraft
        Edited values, with unchanged toggles omitted and invalid devices cleared.
    """
    toggles = {toggle: TOGGLE_CHOICES[index][0] for toggle, index in values.toggle_indices.items()}
    index = values.device_index
    return SceneDraft(
        name=values.name.strip() or base.name,
        toggles={key: value for key, value in toggles.items() if value is not None},
        output_device=(
            values.device_names[index]
            if _FIRST_DEVICE_INDEX <= index < len(values.device_names)
            else _UNCHANGED_DEVICE
        ),
        preserved=draft_from(scene=base).preserved,
    )
