"""Concrete scene ports, backed by Config and the live feature managers.

``ConfigSettingsWriter`` dispatches a value to the right typed GSettings setter.
``CallbackToggles`` and ``CallbackAudio`` route to caller-supplied callables, so
the service never depends on the feature modules directly.

Each toggle carries its own availability predicate rather than one flag for all
three: on a GNOME session without a microphone, two of them work and one does
not, and a scene should report exactly that.
"""

from __future__ import annotations

from collections.abc import Callable

from ...core.config import Config
from .actions import SystemToggle


class ConfigSettingsWriter:
    """Writes a scene's settings through the typed Config wrapper."""

    def __init__(self, config: Config) -> None:
        self._config = config

    def set(self, key: str, value: object) -> None:
        # bool must be checked before int: bool is a subclass of int.
        if isinstance(value, bool):
            self._config.set_bool(key, value)
        elif isinstance(value, int):
            self._config.settings.set_int(key, value)
        elif isinstance(value, str):
            self._config.set_string(key, value)


class CallbackToggles:
    """Routes the system toggles to injected callables and availability checks."""

    def __init__(
        self,
        setters: dict[SystemToggle, Callable[[bool], None]],
        available: Callable[[SystemToggle], bool],
    ) -> None:
        self._setters = setters
        self._available = available

    def supports(self, toggle: SystemToggle) -> bool:
        return toggle in self._setters and self._available(toggle)

    def set_keep_awake(self, on: bool) -> None:
        self._set(SystemToggle.KEEP_AWAKE, on)

    def set_do_not_disturb(self, on: bool) -> None:
        self._set(SystemToggle.DO_NOT_DISTURB, on)

    def set_microphone_muted(self, on: bool) -> None:
        self._set(SystemToggle.MICROPHONE_MUTED, on)

    def _set(self, toggle: SystemToggle, on: bool) -> None:
        setter = self._setters.get(toggle)
        if setter is not None:
            setter(on)


class CallbackAudio:
    """Routes the default-output choice to an injected callable."""

    def __init__(self, set_output: Callable[[str], bool]) -> None:
        self._set_output = set_output

    def set_output_device(self, device: str) -> bool:
        return self._set_output(device)
