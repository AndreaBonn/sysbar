"""Scene service: apply a named list of actions as one unit.

Activating runs every action of a scene and records which one is active.
Clearing drives the system toggles back off; it does not undo settings writes,
because a scene does not remember what a key held before it changed it, and
inventing that history would be a different feature.

The outcome of the last activation is kept so the caller can say how much of a
scene actually took effect. Observable via ``changed``; the ports are faked in
tests, so the orchestration runs without GSettings or live managers.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import ClassVar

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GObject  # noqa: E402

from .actions import SetToggle, SystemToggle  # noqa: E402
from .apply import ActionOutcome, ScenePorts, apply_action, apply_actions  # noqa: E402
from .models import PRESET_SCENES, Scene  # noqa: E402

log = logging.getLogger(__name__)

_ACTIVE_SCENE_KEY = "active-scene"
_NO_SCENE = ""


class SceneService(GObject.Object):
    """Applies and clears scenes, and remembers which one is active."""

    __gsignals__: ClassVar[dict[str, tuple[object, ...]]] = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(
        self,
        ports: ScenePorts,
        scenes: Iterable[Scene] = PRESET_SCENES,
        active_id: str = _NO_SCENE,
    ) -> None:
        super().__init__()
        self._ports = ports
        self._scenes = list(scenes)
        self._active_id = active_id
        self._last_outcomes: list[ActionOutcome] = []

    @property
    def scenes(self) -> list[Scene]:
        return list(self._scenes)

    @property
    def active_id(self) -> str:
        return self._active_id

    @property
    def last_outcomes(self) -> list[ActionOutcome]:
        """What each action of the most recent activation did."""
        return list(self._last_outcomes)

    def set_scenes(self, scenes: Iterable[Scene]) -> None:
        """Replace the known scenes, clearing the active one if it is gone."""
        self._scenes = list(scenes)
        if self._active_id and self.find(self._active_id) is None:
            self._set_active(_NO_SCENE)
        else:
            self.emit("changed")

    def find(self, scene_id: str) -> Scene | None:
        return next((scene for scene in self._scenes if scene.id == scene_id), None)

    def activate(self, scene_id: str) -> None:
        """Run every action of ``scene_id``; unknown ids are ignored."""
        scene = self.find(scene_id)
        if scene is None:
            log.debug("ignoring unknown scene", extra={"scene": scene_id})
            return
        self._last_outcomes = apply_actions(list(scene.actions), self._ports)
        self._set_active(scene_id)

    def clear(self) -> None:
        """Turn the system toggles off and forget the active scene."""
        for toggle in SystemToggle:
            apply_action(SetToggle(toggle=toggle, value=False), self._ports)
        self._last_outcomes = []
        self._set_active(_NO_SCENE)

    def _set_active(self, scene_id: str) -> None:
        self._ports.settings.set(_ACTIVE_SCENE_KEY, scene_id)
        self._active_id = scene_id
        self.emit("changed")
