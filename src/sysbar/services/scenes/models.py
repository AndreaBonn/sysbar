"""Scene model and the built-in presets.

A scene is a named, composable mode that drives several features at once: a few
GSettings values plus the runtime toggles (keep awake, do not disturb, mute
microphone). Activating a scene applies all of them together.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SCENE_FOCUS = "focus"
SCENE_PRESENTATION = "presentation"
SCENE_POWER_SAVING = "power-saving"


@dataclass(frozen=True)
class Scene:
    """A composable mode applied as one unit."""

    id: str
    name: str
    keep_awake: bool
    do_not_disturb: bool
    mute_microphone: bool
    settings: dict[str, object] = field(default_factory=dict)


PRESET_SCENES: tuple[Scene, ...] = (
    Scene(
        id=SCENE_FOCUS,
        name="Focus",
        keep_awake=True,
        do_not_disturb=True,
        mute_microphone=True,
        settings={"alert-enabled": False},
    ),
    Scene(
        id=SCENE_PRESENTATION,
        name="Presentation",
        keep_awake=True,
        do_not_disturb=True,
        mute_microphone=False,
        settings={"clamshell-preferred": False, "default-duration-minutes": 0},
    ),
    Scene(
        id=SCENE_POWER_SAVING,
        name="Power saving",
        keep_awake=False,
        do_not_disturb=False,
        mute_microphone=False,
        settings={"monitor-interval-seconds": 5, "alert-battery-percent": 20},
    ),
)

# Ids of the scenes shipped with the application. Their names are literals in
# this module, so they are in the translation catalogue and are translated for
# display. Names of scenes the user creates are not: passing them through
# gettext would both fail to translate them and, because the catalogue is
# checked in CI, demand a msgid for whatever the user happened to type.
PRESET_SCENE_IDS: frozenset[str] = frozenset(scene.id for scene in PRESET_SCENES)
