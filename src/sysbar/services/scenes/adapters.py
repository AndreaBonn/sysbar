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


class SettingWriteError(ValueError):
    """Raised when a value cannot be written to the key it names."""


# What each schema type expects, so a mismatch is refused before GSettings sees
# it. bool comes before int deliberately: in Python bool is a subclass of int.
_EXPECTED_BY_TYPE: dict[str, type[bool] | type[int] | type[str]] = {
    "b": bool,
    "i": int,
    "s": str,
}


class ConfigSettingsWriter:
    """Writes a scene's settings through the typed Config wrapper.

    Dispatch is on the type the key holds, not on the type of the value.
    GSettings refuses a mismatched write by returning False and logging, without
    raising, so dispatching on the value lets a hand-written manifest produce an
    action that reports itself as applied while nothing was written.
    """

    def __init__(self, config: Config) -> None:
        self._config = config

    def set(self, key: str, value: object) -> None:
        expected = self._expected_type(key)
        if expected is bool and isinstance(value, bool):
            self._config.set_bool(key, value)
        elif expected is int and isinstance(value, int) and not isinstance(value, bool):
            self._config.set_int(key, value)
        elif expected is str and isinstance(value, str):
            self._config.set_string(key, value)
        else:
            raise SettingWriteError(f"{key!r} does not hold {value!r}")

    def _expected_type(self, key: str) -> type[bool] | type[int] | type[str]:
        if not self._config.settings.props.settings_schema.has_key(key):
            raise SettingWriteError(f"no such settings key: {key!r}")
        signature = self._config.settings.get_value(key).get_type_string()
        expected = _EXPECTED_BY_TYPE.get(signature)
        if expected is None:
            raise SettingWriteError(f"a scene cannot write {signature!r} keys: {key!r}")
        return expected


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
