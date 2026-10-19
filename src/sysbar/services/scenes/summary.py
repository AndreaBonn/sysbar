"""A scene described by what it changes, for the line under its name.

"Built in, 4 actions" says how a scene is stored. A user choosing one wants to
know what will happen: the toggles it flips and the device it switches to are
named; settings, which have no short user-facing name, are counted.
"""

from __future__ import annotations

from collections.abc import Callable

from ...core.i18n import _
from .actions import SetOutputDevice, SetSetting, SetToggle, SystemToggle
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
    if settings:
        parts.append(_("+{count} more").format(count=settings))
    return _SEPARATOR.join(parts) if parts else _("Changes nothing yet")
