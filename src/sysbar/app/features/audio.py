"""Per-application mixer and default-device selection.

Both ride on one PulseAudio/PipeWire connection, so they are built together or
not at all: without the capability, or with a backend that refuses to connect,
the feature reports itself unavailable and the panel shows its own explanatory
row rather than an empty section.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ...core.capabilities import PIPEWIRE_PULSE
from ...services.audio.app_volume_mixer import AppVolumeMixer
from ...services.audio.device_switcher import DeviceSwitcher
from ...services.audio.pulse_backend import PulseAudioBackend
from ..context import AppContext

if TYPE_CHECKING:
    from ...ui.panel.panel_window import PanelWindow

log = logging.getLogger(__name__)


class AudioFeature:
    """Owns the audio backend, the per-app mixer and the device switcher."""

    def __init__(self, context: AppContext) -> None:
        self._mixer: AppVolumeMixer | None = None
        self._switcher: DeviceSwitcher | None = None
        if not context.has(PIPEWIRE_PULSE):
            return
        try:
            backend = PulseAudioBackend()
        except Exception as error:
            log.warning("audio backend unavailable", extra={"error": str(error)})
            return
        self._mixer = AppVolumeMixer(backend, context.config)
        self._mixer.start()
        self._switcher = DeviceSwitcher(backend)

    @property
    def is_available(self) -> bool:
        return self._mixer is not None

    def bind_panel(self, panel: PanelWindow) -> None:
        """Attach the mixer and device rows, or mark the section unavailable."""
        if self._mixer is None:
            panel.set_mixer_unavailable()
        else:
            panel.bind_mixer(self._mixer)
        if self._switcher is not None:
            panel.bind_devices(self._switcher)

    def refresh_devices(self) -> None:
        """Re-read the available sinks and sources; no-op without a backend."""
        if self._switcher is not None:
            self._switcher.refresh()
