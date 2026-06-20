"""Interfaces for the quick toggles.

The toggle services depend only on these protocols; ``pulsectl`` and
``Gio.Settings`` are the concrete implementations. Tests inject fakes, so the
toggle logic runs without PipeWire or the GNOME desktop schemas.
"""

from __future__ import annotations

from typing import Protocol


class MicrophoneBackend(Protocol):
    """Reads and controls the default audio source (microphone)."""

    def is_muted(self) -> bool | None: ...
    def set_muted(self, muted: bool) -> None: ...
    def is_in_use(self) -> bool: ...


class GSettingsStore(Protocol):
    """A minimal key/value view over an external GSettings schema."""

    def get_boolean(self, key: str) -> bool: ...
    def set_boolean(self, key: str, value: bool) -> None: ...
    def get_string(self, key: str) -> str: ...
    def set_string(self, key: str, value: str) -> None: ...
