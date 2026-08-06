"""Composable scenes, wired to the features they drive.

The scene service knows nothing about keep awake, the microphone or Do Not
Disturb: it calls a port. This module supplies that port, routing each action to
the feature that owns it, which is why scenes are constructed after them.
"""

from __future__ import annotations

from collections.abc import Callable

from ...services.scenes.adapters import CallbackSceneApplier, ConfigSceneWriter
from ...services.scenes.models import SCENE_FOCUS, Scene
from ...services.scenes.service import SceneService
from .. import tray_state
from ..context import AppContext
from ..tray.menu_builder import SceneMenuEntry
from .keep_awake import KeepAwakeFeature
from .toggles import TogglesFeature

_NO_SCENE = ""
_ACTIVE_SCENE_KEY = "active-scene"


class ScenesFeature:
    """Owns the scene service and routes its actions to the other features."""

    def __init__(
        self,
        context: AppContext,
        keep_awake: KeepAwakeFeature,
        toggles: TogglesFeature,
        on_changed: Callable[[], None],
    ) -> None:
        applier = CallbackSceneApplier(
            keep_awake=keep_awake.set_active,
            do_not_disturb=toggles.set_do_not_disturb,
            microphone_muted=toggles.set_microphone_muted,
        )
        self._service = SceneService(
            ConfigSceneWriter(context.config),
            applier,
            active_id=context.config.get_string(_ACTIVE_SCENE_KEY),
        )
        self._service.connect("changed", lambda _service: on_changed())

    def activate(self, scene_id: str) -> None:
        self._service.activate(scene_id)

    def clear(self) -> None:
        self._service.clear()

    def toggle_focus(self) -> None:
        """Focus is the one scene with a shortcut, so it toggles rather than sets."""
        if self._service.active_id == SCENE_FOCUS:
            self._service.clear()
        else:
            self._service.activate(SCENE_FOCUS)

    def menu_entries(self) -> tuple[SceneMenuEntry, ...]:
        return tray_state.scene_entries(self._service.scenes, self._service.active_id)

    @property
    def scenes(self) -> list[Scene]:
        return self._service.scenes

    @property
    def active_id(self) -> str:
        return self._service.active_id
