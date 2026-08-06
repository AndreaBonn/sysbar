"""Assembling everything the palette can offer, from the live features.

The sources are pure builders in :mod:`sysbar.services.palette.sources`; this is
the one place that knows which of them to call and with what. It is a function
rather than an object because it holds no state: it is called when the palette
opens and again on every keystroke, and each call reads the features as they are
at that moment.

That also settles freshness: nothing is cached, so a clip copied while the
palette is closed is there the next time it opens, and a device unplugged in the
meantime is not.
"""

from __future__ import annotations

from ..services.palette.models import PaletteEntry
from ..services.palette.sources import (
    clipboard_entries,
    device_entries,
    scene_entries,
    shelf_entries,
)
from ..services.scenes.models import scene_display_name
from .commands.actions import CommandHandlers
from .commands.palette import command_entries
from .commands.wiring import current_state
from .features import Features

_OUTPUT_SUBTITLE = "Set as audio output"
_INPUT_SUBTITLE = "Set as audio input"


def collect(features: Features, handlers: CommandHandlers) -> list[PaletteEntry]:
    """Every row the palette could show right now, unranked."""
    entries = command_entries(handlers, current_state(features))
    entries += scene_entries(
        features.scenes.scenes,
        features.scenes.active_id,
        features.scenes.activate,
        scene_display_name,
    )
    entries += clipboard_entries(features.clipboard.entries(), features.clipboard.copy)
    entries += shelf_entries(features.shelf.items(), features.shelf.open_uri)
    entries += device_entries(features.audio.outputs(), features.audio.set_output, _OUTPUT_SUBTITLE)
    entries += device_entries(features.audio.inputs(), features.audio.set_input, _INPUT_SUBTITLE)
    return entries
