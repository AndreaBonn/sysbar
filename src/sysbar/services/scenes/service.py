"""Scene service: apply a composable mode across several features at once.

Activating a scene writes its GSettings values and drives the runtime toggles
(keep awake, do not disturb, mute microphone) through injected ports. Clearing
turns the runtime toggles off again. Observable via ``changed``; both ports are
faked in tests, so the orchestration is unit-tested without GSettings or live
managers.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import ClassVar

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GObject  # noqa: E402

from .models import PRESET_SCENES, Scene  # noqa: E402
from .ports import SceneActionApplier, SettingsWriter  # noqa: E402

log = logging.getLogger(__name__)

_ACTIVE_SCENE_KEY = "active-scene"


class SceneService(GObject.Object):
    """Applies and clears composable scenes."""

    __gsignals__: ClassVar[dict[str, tuple[object, ...]]] = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(
        self,
        writer: SettingsWriter,
        applier: SceneActionApplier,
        scenes: Iterable[Scene] = PRESET_SCENES,
        active_id: str = "",
    ) -> None:
        super().__init__()
        self._writer = writer
        self._applier = applier
        self._scenes = list(scenes)
        self._active_id = active_id

    @property
    def scenes(self) -> list[Scene]:
        return list(self._scenes)

    @property
    def active_id(self) -> str:
        return self._active_id

    def activate(self, scene_id: str) -> None:
        """Apply ``scene_id``'s settings and runtime toggles; ignore unknown ids."""
        scene = next((s for s in self._scenes if s.id == scene_id), None)
        if scene is None:
            return
        for key, value in scene.settings.items():
            self._writer.set(key, value)
        self._apply_runtime(
            keep_awake=scene.keep_awake,
            do_not_disturb=scene.do_not_disturb,
            mute_microphone=scene.mute_microphone,
        )
        self._set_active(scene_id)

    def clear(self) -> None:
        """Turn the scene's runtime toggles off and clear the active scene."""
        self._apply_runtime(keep_awake=False, do_not_disturb=False, mute_microphone=False)
        self._set_active("")

    def _apply_runtime(
        self, *, keep_awake: bool, do_not_disturb: bool, mute_microphone: bool
    ) -> None:
        self._applier.set_keep_awake(keep_awake)
        self._applier.set_do_not_disturb(do_not_disturb)
        self._applier.set_microphone_muted(mute_microphone)

    def _set_active(self, scene_id: str) -> None:
        self._writer.set(_ACTIVE_SCENE_KEY, scene_id)
        self._active_id = scene_id
        self.emit("changed")
