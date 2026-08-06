"""Microphone mute, Do Not Disturb and light/dark, as one feature.

The three share a shape: each needs a capability that may be absent, each is a
flip, and each is rendered as one tray row whose label states what a click will
do. Grouping them means the tray asks for :meth:`TogglesFeature.state` once and
always gets a full answer, instead of testing three nullable services.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from ...core.capabilities import GNOME_DESKTOP, PIPEWIRE_PULSE
from ...core.constants import GNOME_INTERFACE_SCHEMA, GNOME_NOTIFICATIONS_SCHEMA
from ...services.quick_toggles.adapters import GioSettingsStore, PulseMicrophoneBackend
from ...services.quick_toggles.desktop_toggles import ColorSchemeToggle, DoNotDisturbToggle
from ...services.quick_toggles.microphone import MicrophoneToggle
from ..context import AppContext
from ..tray.menu_builder import QuickToggleState

log = logging.getLogger(__name__)


class TogglesFeature:
    """Owns the quick system toggles and reports their combined state."""

    def __init__(self, context: AppContext, on_changed: Callable[[], None]) -> None:
        self._on_changed = on_changed
        self._microphone: MicrophoneToggle | None = None
        self._dnd: DoNotDisturbToggle | None = None
        self._dark_mode: ColorSchemeToggle | None = None
        if context.has(PIPEWIRE_PULSE):
            self._microphone = self._build_microphone()
        if context.has(GNOME_DESKTOP):
            self._dnd = DoNotDisturbToggle(GioSettingsStore(GNOME_NOTIFICATIONS_SCHEMA))
            self._dark_mode = ColorSchemeToggle(GioSettingsStore(GNOME_INTERFACE_SCHEMA))

    @staticmethod
    def _build_microphone() -> MicrophoneToggle | None:
        try:
            return MicrophoneToggle(PulseMicrophoneBackend())
        except Exception as error:
            log.warning("microphone backend unavailable", extra={"error": str(error)})
            return None

    @property
    def any_available(self) -> bool:
        return any((self._microphone, self._dnd, self._dark_mode))

    def state(self) -> QuickToggleState:
        """The full toggle state, with absent backends reported unavailable."""
        microphone, dnd, dark = self._microphone, self._dnd, self._dark_mode
        return QuickToggleState(
            mic_available=microphone is not None,
            mic_muted=microphone.is_muted() if microphone is not None else False,
            mic_in_use=microphone.is_in_use() if microphone is not None else False,
            dnd_available=dnd is not None,
            dnd_active=dnd.is_active() if dnd is not None else False,
            dark_available=dark is not None,
            dark_active=dark.is_dark() if dark is not None else False,
        )

    def toggle_microphone(self) -> None:
        if self._microphone is not None:
            self._microphone.toggle()
            self._on_changed()

    def toggle_do_not_disturb(self) -> None:
        if self._dnd is not None:
            self._dnd.toggle()
            self._on_changed()

    def toggle_dark_mode(self) -> None:
        if self._dark_mode is not None:
            self._dark_mode.toggle()
            self._on_changed()

    def set_microphone_muted(self, muted: bool) -> None:
        """Drive the microphone to a target state; no-op if already there."""
        if self._microphone is not None and self._microphone.is_muted() != muted:
            self._microphone.toggle()

    def set_do_not_disturb(self, active: bool) -> None:
        """Drive Do Not Disturb to a target state; no-op if already there."""
        if self._dnd is not None and self._dnd.is_active() != active:
            self._dnd.toggle()
