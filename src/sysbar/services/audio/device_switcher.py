"""Default audio device selection (output sinks and input sources).

Lets the user switch the system's default output and input from the tray panel.
Switching the output also moves every active stream onto the new sink, so audio
follows the choice immediately instead of only affecting future streams.
Observable via ``devices-changed``; the backend is injected and unit-tested with
a fake.
"""

from __future__ import annotations

import logging
from typing import ClassVar

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GObject  # noqa: E402

from .models import AudioDevice  # noqa: E402
from .ports import DeviceBackend  # noqa: E402

log = logging.getLogger(__name__)


class DeviceSwitcher(GObject.Object):
    """Lists audio devices and applies the default output/input choice."""

    __gsignals__: ClassVar[dict[str, tuple[object, ...]]] = {
        "devices-changed": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, backend: DeviceBackend) -> None:
        super().__init__()
        self._backend = backend
        self._outputs: list[AudioDevice] = []
        self._inputs: list[AudioDevice] = []

    @property
    def outputs(self) -> list[AudioDevice]:
        return list(self._outputs)

    @property
    def inputs(self) -> list[AudioDevice]:
        return list(self._inputs)

    def refresh(self) -> None:
        self._outputs = self._backend.list_sinks()
        self._inputs = self._backend.list_sources()
        self.emit("devices-changed")

    def set_default_output(self, name: str) -> None:
        """Make ``name`` the default sink and move every stream onto it."""
        device = self._find(self._outputs, name)
        if device is None:
            return
        self._backend.set_default_sink(name)
        for sink_input in self._backend.list_sink_inputs():
            self._backend.move_sink_input(sink_input.index, device.index)
        self.refresh()

    def set_default_input(self, name: str) -> None:
        """Make ``name`` the default source."""
        if self._find(self._inputs, name) is None:
            return
        self._backend.set_default_source(name)
        self.refresh()

    @staticmethod
    def _find(devices: list[AudioDevice], name: str) -> AudioDevice | None:
        return next((device for device in devices if device.name == name), None)
