"""Global hotkey manager.

Registers a set of global shortcuts, each gated by its own ``enabled`` predicate
and routed to its own callback. The shortcuts backend is injected, so the
enable/bind decision is unit-tested without a portal.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from .ports import GlobalShortcuts

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class HotkeyBinding:
    """One global shortcut: its id, description, action and enable predicate."""

    shortcut_id: str
    description: str
    trigger: Callable[[], None]
    enabled: Callable[[], bool]


class HotkeyManager:
    """Binds each enabled global shortcut to its action."""

    def __init__(self, shortcuts: GlobalShortcuts, bindings: list[HotkeyBinding]) -> None:
        self._shortcuts = shortcuts
        self._bindings = bindings

    def start(self) -> None:
        """Register every binding whose ``enabled`` predicate is currently true.

        A backend that lacks the GlobalShortcuts portal raises when binding; that
        must degrade to "no hotkeys" rather than take down the application, so a
        failing bind is logged and the remaining bindings still get a chance.
        """
        for binding in self._bindings:
            if not binding.enabled():
                log.debug("global hotkey disabled; not binding", extra={"id": binding.shortcut_id})
                continue
            try:
                self._shortcuts.bind(binding.shortcut_id, binding.description, binding.trigger)
            except Exception as error:
                log.warning(
                    "could not register global shortcut",
                    extra={"id": binding.shortcut_id, "error": str(error)},
                )
