"""Interfaces for the audio mixer.

The mixer service depends only on these protocols; ``pulsectl`` and GSettings
are the concrete implementations. Tests inject fakes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from .models import SinkInput


class AudioBackend(Protocol):
    """Enumerates and controls audio streams."""

    def list_sink_inputs(self) -> list[SinkInput]: ...
    def set_volume(self, index: int, volume: float) -> None: ...
    def set_mute(self, index: int, muted: bool) -> None: ...
    def subscribe(self, callback: Callable[[], None]) -> None: ...


class VolumeStore(Protocol):
    """Persists per-application volumes."""

    def get_app_volumes(self) -> dict[str, float]: ...
    def set_app_volume(self, app_id: str, volume: float) -> None: ...
