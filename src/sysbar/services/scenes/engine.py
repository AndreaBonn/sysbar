"""Driving scene activation from what the sources report.

Holds the little state the decision needs (what was engaged, which rule owns the
active scene, when the last activation happened) and hands the rest to the pure
:func:`sysbar.services.scenes.triggers.evaluate`.

The clock is injected, so the rate limit is testable with a list of timestamps
instead of by waiting. That limit is a backstop, not the main defence: the
engine already produces no command when the state has not changed, so a source
would have to report genuine nonsense for it to matter. It exists because the
cost of one is a few lines and the cost of a scene flapping is the user turning
the whole feature off.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from .constants import TRIGGER_MIN_INTERVAL_SECONDS
from .triggers import TriggerMemory, TriggerRule, TriggerState, evaluate

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TriggerActions:
    """What the engine does once it has decided."""

    activate: Callable[[str], None]
    clear: Callable[[], None]
    announce: Callable[[str], None]


class TriggerEngine:
    """Turns reported state into scene changes, at most one per interval."""

    def __init__(
        self,
        rules: Callable[[], list[TriggerRule]],
        actions: TriggerActions,
        clock: Callable[[], float],
    ) -> None:
        self._rules = rules
        self._actions = actions
        self._clock = clock
        self._memory = TriggerMemory()
        self._last_activation: float | None = None

    @property
    def owned_scene(self) -> str | None:
        """The scene a rule currently holds, if any."""
        return self._memory.owner.scene_id if self._memory.owner is not None else None

    def note_active_scene(self, scene_id: str) -> None:
        """Record what is active now, whoever set it.

        Called when the user changes scene by hand, so the next evaluation knows
        not to treat that choice as its own.
        """
        self._memory = TriggerMemory(
            engaged=self._memory.engaged,
            owner=self._memory.owner,
            active_scene_id=scene_id,
        )

    def update(self, state: TriggerState) -> None:
        """Feed the current state in and act on what it means."""
        decision = evaluate(self._rules(), state, self._memory)
        self._memory = TriggerMemory(
            engaged=decision.engaged,
            owner=decision.owner,
            active_scene_id=self._memory.active_scene_id,
        )
        if decision.is_noop:
            return
        if not self._allowed():
            log.warning("trigger suppressed by the rate limit")
            return
        self._last_activation = self._clock()
        self._perform(decision.activate, clear=decision.clear)

    def _perform(self, scene_id: str | None, *, clear: bool) -> None:
        if scene_id is not None:
            self._actions.activate(scene_id)
            self.note_active_scene(scene_id)
            self._actions.announce(scene_id)
            return
        if clear:
            self._actions.clear()
            self.note_active_scene("")

    def _allowed(self) -> bool:
        if self._last_activation is None:
            return True
        return self._clock() - self._last_activation >= TRIGGER_MIN_INTERVAL_SECONDS
