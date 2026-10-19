"""Decide scene form choices, drafts and list content independently of GTK.

The editor builds widgets and saves scenes; choice ordering, row visibility and
form interpretation live here so they can be checked without a display.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum, auto

from ..services.audio.models import AudioDevice
from ..services.scenes.actions import SystemToggle
from ..services.scenes.editing import SceneDraft, TriggerChoice, draft_from
from ..services.scenes.models import PRESET_SCENE_IDS, Scene
from .device_choices import FIRST_DEVICE_INDEX

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


class RemovalKind(Enum):
    """The action available when removing a scene from the list."""

    RESTORE = auto()
    DELETE = auto()


REMOVAL_PRESENTATIONS: dict[RemovalKind, tuple[str, str]] = {
    RemovalKind.RESTORE: ("edit-undo-symbolic", "Restore the built-in"),
    RemovalKind.DELETE: ("user-trash-symbolic", "Delete"),
}


def removal_kind(scene: Scene) -> RemovalKind | None:
    """Choose whether removing the scene restores a preset or deletes it.

    Parameters
    ----------
    scene : Scene
        Scene displayed in the list.

    Returns
    -------
    RemovalKind or None
        Available removal action, absent for an unmodified built-in.
    """
    if scene.is_built_in:
        return None
    # A customised built-in keeps its id, so it can be restored rather than
    # deleted: there is a shipped version to fall back to.
    return RemovalKind.RESTORE if scene.id in PRESET_SCENE_IDS else RemovalKind.DELETE


def device_descriptions(outputs: Sequence[AudioDevice]) -> dict[str, str]:
    """Map audio identifiers to their nonempty readable descriptions.

    Parameters
    ----------
    outputs : Sequence[AudioDevice]
        Output devices read by the window.

    Returns
    -------
    dict[str, str]
        Descriptions suitable for scene subtitles, keyed by device name.
    """
    return {device.name: device.description for device in outputs if device.description}


@dataclass(frozen=True)
class FormValues:
    """Widget values needed to interpret a scene form without GTK."""

    name: str
    toggle_indices: Mapping[SystemToggle, int]
    device_index: int
    device_names: tuple[str, ...]


def trigger_rows_visibility(choice: TriggerChoice) -> tuple[bool, bool]:
    """Visibility of the (percentage, restore) rows for a trigger condition.

    Only the threshold condition has a percentage to ask about; every
    condition but "never" can restore the previous scene when it ends.
    """
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
            if FIRST_DEVICE_INDEX <= index < len(values.device_names)
            else _UNCHANGED_DEVICE
        ),
        preserved=draft_from(scene=base).preserved,
    )
