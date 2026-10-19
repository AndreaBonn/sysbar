"""A scene described by what it changes, for the line under its name.

"Built in, 4 actions" says how a scene is stored. A user choosing one wants to
know what will happen: the toggles it flips and the device it switches to are
named; settings, which have no short user-facing name, are counted. The module
also words an activation's outcome: how much of a scene took effect.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import assert_never

from ...core.i18n import _
from .actions import SetOutputDevice, SetSetting, SetToggle, SystemToggle
from .apply import ActionOutcome, applied_count
from .models import Scene

_SEPARATOR = " · "
_TOGGLE_PHRASES = {
    (SystemToggle.KEEP_AWAKE, True): "Keep awake on",
    (SystemToggle.KEEP_AWAKE, False): "Keep awake off",
    (SystemToggle.DO_NOT_DISTURB, True): "Do Not Disturb on",
    (SystemToggle.DO_NOT_DISTURB, False): "Do Not Disturb off",
    (SystemToggle.MICROPHONE_MUTED, True): "Microphone muted",
    (SystemToggle.MICROPHONE_MUTED, False): "Microphone on",
}


def describe_scene(scene: Scene, *, device_name: Callable[[str], str | None] | None = None) -> str:
    """Name the toggles and device a scene sets, then count its other settings.

    ``device_name`` maps a sink name to its readable description; a device it
    does not know (unplugged, say) falls back to the sink name.
    """
    parts: list[str] = []
    settings = 0
    for action in scene.actions:
        match action:
            case SetToggle(toggle=toggle, value=value):
                parts.append(_(_TOGGLE_PHRASES[(toggle, value)]))
            case SetOutputDevice(device=device):
                readable = device_name(device) if device_name is not None else None
                parts.append(_("Audio to {device}").format(device=readable or device))
            case SetSetting():
                settings += 1
            case _:  # pragma: no cover
                assert_never(action)
    if settings:
        parts.append(_("+{count} more").format(count=settings))
    return _SEPARATOR.join(parts) if parts else _("Changes nothing yet")


def partial_note(outcomes: list[ActionOutcome], scene_name: str) -> str:
    """How much of an activation took effect, empty when all of it did.

    An action whose capability is missing is a skip, not a failure, so the
    scene still counts as activated. Saying nothing about it is how a scene
    quietly does half of what its name promises.
    """
    applied = applied_count(outcomes)
    if not outcomes or applied == len(outcomes):
        return ""
    return _("{applied} of {total} actions in {scene} took effect.").format(
        applied=applied, total=len(outcomes), scene=scene_name
    )


def trigger_announcement(scene_name: str, outcomes: list[ActionOutcome]) -> str:
    """Name the triggered scene, reporting any actions that did not take effect."""
    return partial_note(outcomes=outcomes, scene_name=scene_name) or _(
        "A trigger switched to {scene}."
    ).format(scene=scene_name)
