"""Pointer shake detection.

A shake is a burst of rapid horizontal direction reversals within a short time
window. The detector is fed raw pointer motion deltas and returns ``True`` once
a shake is recognized. Pure and unit-tested; the X11 motion source is separate.
"""

from __future__ import annotations

from collections import deque

from ...core.constants import (
    SHAKE_MIN_MOVE_PIXELS,
    SHAKE_REQUIRED_REVERSALS,
    SHAKE_WINDOW_SECONDS,
)


class ShakeDetector:
    """Detect a shake from a stream of pointer motion deltas."""

    def __init__(
        self,
        min_move: float = SHAKE_MIN_MOVE_PIXELS,
        window_seconds: float = SHAKE_WINDOW_SECONDS,
        required_reversals: int = SHAKE_REQUIRED_REVERSALS,
    ) -> None:
        self._min_move = min_move
        self._window = window_seconds
        self._required = required_reversals
        self._last_sign = 0
        self._reversals: deque[float] = deque()

    def reset(self) -> None:
        self._last_sign = 0
        self._reversals.clear()

    def feed(self, dx: float, timestamp: float) -> bool:
        """Feed one horizontal motion sample; return ``True`` when a shake is detected."""
        if abs(dx) < self._min_move:
            return False
        sign = 1 if dx > 0 else -1
        if self._last_sign and sign != self._last_sign:
            self._reversals.append(timestamp)
        self._last_sign = sign
        self._prune(timestamp)
        if len(self._reversals) >= self._required:
            self.reset()
            return True
        return False

    def _prune(self, now: float) -> None:
        cutoff = now - self._window
        while self._reversals and self._reversals[0] < cutoff:
            self._reversals.popleft()
