"""Interfaces the scene service drives.

The service depends only on these protocols; GSettings and the live feature
managers are the concrete implementations. Tests inject fakes.
"""

from __future__ import annotations

from typing import Protocol


class SettingsWriter(Protocol):
    """Writes a configuration value of any supported type."""

    def set(self, key: str, value: object) -> None: ...


class SceneActionApplier(Protocol):
    """Drives the runtime feature toggles a scene controls."""

    def set_keep_awake(self, on: bool) -> None: ...
    def set_do_not_disturb(self, on: bool) -> None: ...
    def set_microphone_muted(self, on: bool) -> None: ...
