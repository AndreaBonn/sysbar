"""PulseAudio/PipeWire backend via ``pulsectl``.

Boundary code: enumerates sink-inputs, sets per-stream volume/mute, and runs a
dedicated event-listening connection on a daemon thread for live updates. The
grouping/persistence logic that consumes it is unit-tested separately.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from .models import SinkInput

log = logging.getLogger(__name__)

_CLIENT_NAME = "sysbar-mixer"
_EVENTS_CLIENT_NAME = "sysbar-mixer-events"
_SINK_INPUT = "sink_input"


class PulseAudioBackend:
    """Controls audio streams through ``pulsectl``."""

    def __init__(self) -> None:  # pragma: no cover - pulsectl connection boundary
        import pulsectl

        self._pulsectl = pulsectl
        self._pulse = pulsectl.Pulse(_CLIENT_NAME)
        self._callback: Callable[[], None] | None = None
        self._listen_thread: threading.Thread | None = None
        self._running = False

    def list_sink_inputs(self) -> list[SinkInput]:
        return [self._to_sink_input(si) for si in self._pulse.sink_input_list()]

    def set_volume(  # pragma: no cover - pulsectl connection boundary
        self, index: int, volume: float
    ) -> None:
        sink_input = self._pulse.sink_input_info(index)
        self._pulse.volume_set_all_chans(sink_input, volume)

    def set_mute(self, index: int, muted: bool) -> None:  # pragma: no cover - pulsectl boundary
        self._pulse.sink_input_mute(index, muted)

    def subscribe(self, callback: Callable[[], None]) -> None:
        self._callback = callback
        if self._listen_thread is not None:
            return
        self._running = True
        self._listen_thread = threading.Thread(target=self._listen, daemon=True)
        self._listen_thread.start()

    def _to_sink_input(self, raw: Any) -> SinkInput:
        proplist = getattr(raw, "proplist", {}) or {}
        pid = proplist.get("application.process.id")
        return SinkInput(
            index=raw.index,
            app_id=proplist.get("application.id"),
            binary=proplist.get("application.process.binary"),
            name=proplist.get("application.name"),
            pid=int(pid) if pid is not None and str(pid).isdigit() else None,
            volume=float(raw.volume.value_flat),
            muted=bool(raw.mute),
            corked=bool(raw.corked),
        )

    def _listen(self) -> None:  # pragma: no cover - pulsectl event-loop boundary
        with self._pulsectl.Pulse(_EVENTS_CLIENT_NAME) as pulse:
            pulse.event_mask_set(_SINK_INPUT)
            pulse.event_callback_set(self._on_pulse_event)
            while self._running:
                pulse.event_listen(timeout=1.0)

    def _on_pulse_event(self, _event: object) -> None:
        if self._callback is not None:
            self._callback()
        raise self._pulsectl.PulseLoopStop
