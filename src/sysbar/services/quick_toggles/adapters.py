"""Concrete backends for the quick toggles (the system boundary).

``PulseMicrophoneBackend`` talks to PipeWire/PulseAudio through ``pulsectl``;
``GioSettingsStore`` wraps a single external ``Gio.Settings`` schema. Both are
thin and mocked in tests via their ports.
"""

from __future__ import annotations

import logging
from typing import Any

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio  # noqa: E402

log = logging.getLogger(__name__)

_CLIENT_NAME = "sysbar-mic"


class PulseMicrophoneBackend:  # pragma: no cover - pulsectl connection boundary
    """Controls the default source and detects active capture via ``pulsectl``."""

    def __init__(self) -> None:
        import pulsectl

        self._pulse = pulsectl.Pulse(_CLIENT_NAME)

    def is_muted(self) -> bool | None:
        source = self._default_source()
        return bool(source.mute) if source is not None else None

    def set_muted(self, muted: bool) -> None:
        source = self._default_source()
        if source is not None:
            self._pulse.source_mute(source.index, muted)

    def is_in_use(self) -> bool:
        return bool(self._pulse.source_output_list())

    def _default_source(self) -> Any | None:
        name = self._pulse.server_info().default_source_name
        for source in self._pulse.source_list():
            if source.name == name:
                return source
        return None


class GioSettingsStore:  # pragma: no cover - Gio.Settings boundary
    """A :class:`GSettingsStore` backed by one external GSettings schema."""

    def __init__(self, schema_id: str) -> None:
        self._settings = Gio.Settings.new(schema_id)

    def get_boolean(self, key: str) -> bool:
        return bool(self._settings.get_boolean(key))

    def set_boolean(self, key: str, value: bool) -> None:
        self._settings.set_boolean(key, value)

    def get_string(self, key: str) -> str:
        return str(self._settings.get_string(key))

    def set_string(self, key: str, value: str) -> None:
        self._settings.set_string(key, value)
