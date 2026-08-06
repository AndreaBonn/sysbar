"""What the scene windows need from the feature that owns the scenes."""

from __future__ import annotations

from typing import Protocol

from ...services.audio.models import AudioDevice
from ...services.scenes.models import Scene
from ...services.scenes.triggers import TriggerRule


class SceneController(Protocol):
    """The narrow surface the list and the form talk to."""

    @property
    def scenes(self) -> list[Scene]: ...

    def save(self, scene: Scene) -> None: ...
    def delete(self, scene_id: str) -> bool: ...
    def outputs(self) -> list[AudioDevice]: ...
    def trigger_for(self, scene_id: str) -> TriggerRule | None: ...
    def save_trigger(self, rule: TriggerRule | None, scene_id: str) -> None: ...
