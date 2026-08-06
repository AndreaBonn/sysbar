"""What a scene is, and the ones shipped with the application.

A scene is a name and an ordered list of actions. Built-in scenes and ones the
user writes are the same type, told apart by ``origin`` rather than by a
``modified`` flag: a flag would admit "a built-in that has been changed", which
is neither one thing nor the other and would have to be given a meaning.

Editing a built-in therefore produces a user scene keeping the same id, an
override. Restoring the built-in is deleting the override, and nothing ever
mutates the constants below.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum

from .actions import (
    SceneAction,
    SceneActionError,
    SetSetting,
    SetToggle,
    SystemToggle,
    action_from_dict,
    action_to_dict,
)

SCENE_FOCUS = "focus"
SCENE_PRESENTATION = "presentation"
SCENE_POWER_SAVING = "power-saving"


class SceneOrigin(StrEnum):
    """Whether a scene ships with the application or was written by the user."""

    BUILT_IN = "built-in"
    USER = "user"


class SceneError(ValueError):
    """Raised when stored scene data cannot be read back."""


@dataclass(frozen=True)
class Scene:
    """A named list of actions, applied as one unit."""

    id: str
    name: str
    actions: tuple[SceneAction, ...] = field(default_factory=tuple)
    origin: SceneOrigin = SceneOrigin.BUILT_IN

    def __post_init__(self) -> None:
        if not self.id:
            raise SceneError("a scene needs an id")
        if not self.name.strip():
            raise SceneError("a scene needs a name")

    @property
    def is_built_in(self) -> bool:
        return self.origin is SceneOrigin.BUILT_IN

    def edited(self, *, name: str | None = None, actions: tuple[SceneAction, ...] | None) -> Scene:
        """A user-owned copy carrying the change.

        Editing a built-in never mutates it: the result is a user scene with the
        same id, which the store keeps as an override.
        """
        return replace(
            self,
            name=self.name if name is None else name,
            actions=self.actions if actions is None else actions,
            origin=SceneOrigin.USER,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "origin": self.origin.value,
            "actions": [action_to_dict(action) for action in self.actions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Scene:
        """Rebuild a scene, raising on anything it cannot make sense of."""
        raw_actions = data.get("actions", [])
        if not isinstance(raw_actions, list):
            raise SceneError(f"actions must be a list, got {type(raw_actions).__name__}")
        try:
            actions = tuple(action_from_dict(item) for item in raw_actions)
        except (SceneActionError, AttributeError, TypeError) as error:
            raise SceneError(str(error)) from error
        try:
            origin = SceneOrigin(str(data.get("origin", SceneOrigin.USER.value)))
        except ValueError as error:
            raise SceneError(f"unknown scene origin: {data.get('origin')!r}") from error
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            actions=actions,
            origin=origin,
        )


def _toggles(
    *, keep_awake: bool, do_not_disturb: bool, microphone_muted: bool
) -> tuple[SceneAction, ...]:
    return (
        SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=keep_awake),
        SetToggle(toggle=SystemToggle.DO_NOT_DISTURB, value=do_not_disturb),
        SetToggle(toggle=SystemToggle.MICROPHONE_MUTED, value=microphone_muted),
    )


PRESET_SCENES: tuple[Scene, ...] = (
    Scene(
        id=SCENE_FOCUS,
        name="Focus",
        actions=(
            *_toggles(keep_awake=True, do_not_disturb=True, microphone_muted=True),
            SetSetting(key="alert-enabled", value=False),
        ),
    ),
    Scene(
        id=SCENE_PRESENTATION,
        name="Presentation",
        actions=(
            *_toggles(keep_awake=True, do_not_disturb=True, microphone_muted=False),
            SetSetting(key="clamshell-preferred", value=False),
            SetSetting(key="default-duration-minutes", value=0),
        ),
    ),
    Scene(
        id=SCENE_POWER_SAVING,
        name="Power saving",
        actions=(
            *_toggles(keep_awake=False, do_not_disturb=False, microphone_muted=False),
            SetSetting(key="monitor-interval-seconds", value=5),
            SetSetting(key="alert-battery-percent", value=20),
        ),
    ),
)

# Ids of the scenes shipped with the application. Their names are literals in
# this module, so they are in the translation catalogue and are translated for
# display. Names of scenes the user creates are not: passing them through
# gettext would both fail to translate them and, because the catalogue is
# checked in CI, demand a msgid for whatever the user happened to type.
PRESET_SCENE_IDS: frozenset[str] = frozenset(scene.id for scene in PRESET_SCENES)
