"""Watching the display layout for the scene triggers.

The only source that needs its own adapter. Power and battery already arrive
through the monitor's snapshot stream, so feeding those to the engine costs a
method call; the display does not appear anywhere else in the application.

Gdk has no notion of "the built-in panel", so an external monitor is inferred
from there being more than one. That is right on a laptop, which is the case the
trigger exists for, and harmless on a desktop with one screen. On a desktop with
two permanently attached screens the condition simply holds all the time, and a
rule using it never fires a transition.

Hotplugging one monitor emits several changes in a row while the layout settles,
so reports are debounced. Without it the engine would see two or three different
states for one physical action.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gdk, GLib  # noqa: E402

from ...services.scenes.constants import MONITOR_DEBOUNCE_MS  # noqa: E402

log = logging.getLogger(__name__)

_NO_TIMER = 0
_SINGLE_DISPLAY = 1


class DisplayWatcher:
    """Reports whether more than one monitor is attached, once things settle."""

    def __init__(self, on_change: Callable[[bool], None]) -> None:
        self._on_change = on_change
        self._pending = _NO_TIMER
        self._monitors = self._attach()

    @property
    def has_external_monitor(self) -> bool:
        if self._monitors is None:
            return False
        return bool(self._monitors.get_n_items() > _SINGLE_DISPLAY)

    def _attach(self) -> Gdk.Display | None:
        display = Gdk.Display.get_default()
        if display is None:
            log.warning("no display; the monitor trigger stays inactive")
            return None
        monitors = display.get_monitors()
        monitors.connect("items-changed", self._on_items_changed)
        return monitors

    def _on_items_changed(self, *_args: object) -> None:
        if self._pending:
            GLib.source_remove(self._pending)
        self._pending = GLib.timeout_add(MONITOR_DEBOUNCE_MS, self._report)

    def _report(self) -> bool:
        self._pending = _NO_TIMER
        self._on_change(self.has_external_monitor)
        return False
