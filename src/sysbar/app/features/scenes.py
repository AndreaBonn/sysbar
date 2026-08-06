"""Composable scenes, wired to the features they drive.

The scene service knows nothing about keep awake, the microphone or Do Not
Disturb: it calls ports. This module supplies them, routing each action to the
feature that owns it, which is why scenes are constructed after those.

Availability is asked per toggle rather than once for all three: on a session
with Do Not Disturb but no microphone, a scene should apply what it can and
report the rest as skipped, not fail whole.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from ...core.i18n import _
from ...services.audio.models import AudioDevice
from ...services.scenes.actions import SystemToggle
from ...services.scenes.adapters import CallbackAudio, CallbackToggles, ConfigSettingsWriter
from ...services.scenes.apply import ScenePorts
from ...services.scenes.editing import rule_id_for
from ...services.scenes.engine import TriggerActions, TriggerEngine
from ...services.scenes.models import SCENE_FOCUS, Scene
from ...services.scenes.service import SceneService
from ...services.scenes.store import SceneStore
from ...services.scenes.triggers import TriggerRule, TriggerState
from .. import tray_state
from ..context import AppContext
from ..tray.menu_builder import SceneMenuEntry
from ..windows import WindowSlot
from .audio import AudioFeature
from .keep_awake import KeepAwakeFeature
from .toggles import TogglesFeature
from .trigger_sources import DisplayWatcher

if TYPE_CHECKING:
    from ...ui.scenes.scenes_window import ScenesWindow

_ACTIVE_SCENE_KEY = "active-scene"
_TRIGGERS_ENABLED_KEY = "scene-triggers-enabled"


class ScenesFeature:
    """Owns the scene service and routes its actions to the other features."""

    def __init__(
        self,
        context: AppContext,
        drivers: SceneDrivers,
        on_changed: Callable[[], None],
    ) -> None:
        self._drivers = drivers
        self._store = SceneStore()
        self._store.load()
        self._service = SceneService(
            drivers.ports(context),
            scenes=self._store.all_scenes(),
            active_id=context.config.get_string(_ACTIVE_SCENE_KEY),
        )
        self._on_changed = on_changed
        self._service.connect("changed", lambda _service: self._scene_changed())
        self._window: WindowSlot[ScenesWindow] = WindowSlot(self._build_window)
        self._context = context
        self._state = TriggerState()
        self._engine = self._build_engine()
        self._display = DisplayWatcher(self._on_display_changed)
        self._refresh_triggers()

    def _build_engine(self) -> TriggerEngine:
        """The engine, started level with whatever scene is already active."""
        engine = TriggerEngine(
            lambda: self._store.triggers,
            TriggerActions(
                activate=self._service.activate,
                clear=self._service.clear,
                announce=self._announce,
            ),
            time.monotonic,
        )
        engine.note_active_scene(self._service.active_id)
        return engine

    # --- triggers ---------------------------------------------------------

    @property
    def triggers_enabled(self) -> bool:
        return self._context.config.get_bool(_TRIGGERS_ENABLED_KEY)

    def note_snapshot(self, on_battery: bool, battery_percent: float | None) -> None:
        """Feed the power state from the monitor's sample stream."""
        self._state = TriggerState(
            external_monitor=self._state.external_monitor,
            on_battery=on_battery,
            battery_percent=battery_percent,
        )
        self._refresh_triggers()

    def _on_display_changed(self, has_external: bool) -> None:
        self._state = TriggerState(
            external_monitor=has_external,
            on_battery=self._state.on_battery,
            battery_percent=self._state.battery_percent,
        )
        self._refresh_triggers()

    def _refresh_triggers(self) -> None:
        """Evaluate the rules, unless the user has switched triggers off."""
        if not self.triggers_enabled:
            return
        self._engine.update(self._state)

    def _announce(self, scene_id: str) -> None:
        """Say which scene a trigger just applied.

        A scene changing without the user asking is exactly the kind of thing
        that reads as the machine misbehaving unless it says what it did.
        """
        scene = self._service.find(scene_id)
        name = scene.name if scene is not None else scene_id
        self._context.notifier.notify(
            _("Scene activated"),
            _("A trigger switched to {scene}.").format(scene=name),
            notification_id="scene-trigger",
        )

    def open(self) -> None:
        self._window.present()

    def _build_window(self) -> ScenesWindow:
        from ...ui.scenes.scenes_window import ScenesWindow

        return ScenesWindow(self)

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

    def trigger_for(self, scene_id: str) -> TriggerRule | None:
        """The rule the editor owns for this scene, if there is one."""
        wanted = rule_id_for(scene_id)
        return next((rule for rule in self._store.triggers if rule.id == wanted), None)

    def save_trigger(self, rule: TriggerRule | None, scene_id: str) -> None:
        """Store the rule the form describes, or drop the scene's rule for "never"."""
        if rule is None:
            self._store.remove_trigger(rule_id_for(scene_id))
        else:
            self._store.upsert_trigger(rule)
        self._refresh_triggers()

    def outputs(self) -> list[AudioDevice]:
        """Audio outputs a scene can pick from, empty without a backend."""
        return self._drivers.available_outputs()

    def is_overridden(self, scene_id: str) -> bool:
        """Whether a built-in has been customised and can be restored."""
        return self._store.is_overridden(scene_id)

    def _scene_changed(self) -> None:
        """Keep the engine level with the service, whoever moved the scene.

        Every route into a scene change ends at the service's ``changed``
        signal, so listening here is what makes "the user chose this by hand"
        true for the menu, the shortcut, the palette and the command line alike.
        Asking each caller to announce itself works until one forgets, and the
        one that forgot lets a trigger overwrite a scene the user picked.
        """
        self._engine.note_active_scene(self._service.active_id)
        self._on_changed()

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

    def available_outputs(self) -> list[AudioDevice]:
        return self._audio.outputs()

    def _set_output(self, device: str) -> bool:
        """Select ``device`` if it is currently connected."""
        if device not in {available.name for available in self._audio.outputs()}:
            return False
        self._audio.set_output(device)
        return True
