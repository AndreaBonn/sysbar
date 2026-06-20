"""Global microphone mute toggle and in-use indicator.

Wraps a :class:`MicrophoneBackend` (PipeWire/PulseAudio default source) with the
small amount of decision logic the menu needs. The backend is injected, so this
logic is unit-tested without a real audio server.
"""

from __future__ import annotations

import logging

from .ports import MicrophoneBackend

log = logging.getLogger(__name__)


class MicrophoneToggle:
    """Mute/unmute the default source and report whether it is recording."""

    def __init__(self, backend: MicrophoneBackend) -> None:
        self._backend = backend

    def is_muted(self) -> bool:
        """Whether the default source is muted (``False`` when there is none)."""
        return bool(self._backend.is_muted())

    def is_in_use(self) -> bool:
        """Whether any application is currently capturing from a source."""
        return self._backend.is_in_use()

    def toggle(self) -> None:
        """Flip the mute state; a no-op when there is no default source."""
        muted = self._backend.is_muted()
        if muted is None:
            log.debug("no default source; microphone toggle ignored")
            return
        self._backend.set_muted(not muted)
