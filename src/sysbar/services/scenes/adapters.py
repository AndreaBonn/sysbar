"""Concrete scene ports backed by Config and the live feature managers.

``ConfigSceneWriter`` dispatches a value to the right typed GSettings setter.
``CallbackSceneApplier`` routes the runtime toggles to caller-supplied callables,
so the application can wire keep-awake, do-not-disturb and microphone without the
service depending on those managers directly.
"""

from __future__ import annotations

from collections.abc import Callable

from ...core.config import Config


class ConfigSceneWriter:
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


class CallbackSceneApplier:
    """Routes the runtime scene toggles to injected callables."""

    def __init__(
        self,
        keep_awake: Callable[[bool], None],
        do_not_disturb: Callable[[bool], None],
        microphone_muted: Callable[[bool], None],
    ) -> None:
        self._keep_awake = keep_awake
        self._do_not_disturb = do_not_disturb
        self._microphone_muted = microphone_muted

    def set_keep_awake(self, on: bool) -> None:
        self._keep_awake(on)

    def set_do_not_disturb(self, on: bool) -> None:
        self._do_not_disturb(on)

    def set_microphone_muted(self, on: bool) -> None:
        self._microphone_muted(on)
