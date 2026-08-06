"""Composable scenes, wired to the features they drive.

The scene service knows nothing about keep awake, the microphone or Do Not
Disturb: it calls ports. This module supplies them, routing each action to the
feature that owns it, which is why scenes are constructed after those.

Availability is asked per toggle rather than once for all three: on a session
with Do Not Disturb but no microphone, a scene should apply what it can and
report the rest as skipped, not fail whole.
"""

from __future__ import annotations

from collections.abc import Callable

from ...services.scenes.actions import SystemToggle
from ...services.scenes.adapters import CallbackAudio, CallbackToggles, ConfigSettingsWriter
from ...services.scenes.apply import ScenePorts
from ...services.scenes.models import SCENE_FOCUS, Scene
from ...services.scenes.service import SceneService
from ...services.scenes.store import SceneStore
from .. import tray_state
from ..context import AppContext
from ..tray.menu_builder import SceneMenuEntry
from .audio import AudioFeature
from .keep_awake import KeepAwakeFeature
from .toggles import TogglesFeature

_ACTIVE_SCENE_KEY = "active-scene"


class ScenesFeature:
    """Owns the scene service and routes its actions to the other features."""

    def __init__(
        self,
        context: AppContext,
        drivers: SceneDrivers,
        on_changed: Callable[[], None],
    ) -> None:
        self._store = SceneStore()
        self._store.load()
        self._service = SceneService(
            drivers.ports(context),
            scenes=self._store.all_scenes(),
            active_id=context.config.get_string(_ACTIVE_SCENE_KEY),
        )
        self._service.connect("changed", lambda _service: on_changed())

    def save(self, scene: Scene) -> None:
        """Create or replace a scene, then republish the list."""
        self._store.upsert(scene)
        self._service.set_scenes(self._store.all_scenes())

    def delete(self, scene_id: str) -> bool:
        """Remove a user scene, or restore a built-in by dropping its override."""
        if not self._store.remove(scene_id):
            return False
        self._service.set_scenes(self._store.all_scenes())
        return True

    def is_overridden(self, scene_id: str) -> bool:
        """Whether a built-in has been customised and can be restored."""
        return self._store.is_overridden(scene_id)

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


class SceneDrivers:
    """The features a scene acts on, bundled so the constructor stays narrow."""

    def __init__(
        self, keep_awake: KeepAwakeFeature, toggles: TogglesFeature, audio: AudioFeature
    ) -> None:
        self._keep_awake = keep_awake
        self._toggles = toggles
        self._audio = audio

    def ports(self, context: AppContext) -> ScenePorts:
        return ScenePorts(
            toggles=CallbackToggles(
                setters={
                    SystemToggle.KEEP_AWAKE: self._keep_awake.set_active,
                    SystemToggle.DO_NOT_DISTURB: self._toggles.set_do_not_disturb,
                    SystemToggle.MICROPHONE_MUTED: self._toggles.set_microphone_muted,
                },
                available=self._supports,
            ),
            settings=ConfigSettingsWriter(context.config),
            audio=CallbackAudio(set_output=self._set_output),
        )

    def _supports(self, toggle: SystemToggle) -> bool:
        state = self._toggles.state()
        match toggle:
            case SystemToggle.KEEP_AWAKE:
                return True
            case SystemToggle.DO_NOT_DISTURB:
                return state.dnd_available
            case SystemToggle.MICROPHONE_MUTED:
                return state.mic_available

    def _set_output(self, device: str) -> bool:
        """Select ``device`` if it is currently connected."""
        if device not in {available.name for available in self._audio.outputs()}:
            return False
        self._audio.set_output(device)
        return True
