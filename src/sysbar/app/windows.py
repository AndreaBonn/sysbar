"""Lazy, self-clearing slots for the application's secondary windows.

Every window in Sysbar follows the same life cycle: build it the first time it
is asked for, present it on later requests, and drop the reference when the user
closes it so the next request builds a fresh one. That was written out six times,
once per window, as a ``_open_x`` / ``_on_x_closed`` pair plus a nullable
attribute.

The nullable attribute is the part worth removing: it leaked into every caller
that wanted to push an update into an open window, as ``if self._panel is not
None``. :meth:`WindowSlot.if_open` does that check once, here.

Rebuilding rather than hiding is deliberate: a window that is recreated on each
open picks up hardware and capability changes that a long-lived hidden window
would keep showing stale (see the note on Settings in ``docs/DESIGN_DECISIONS.md``).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Generic, Protocol, TypeVar

_CLOSE_REQUEST = "close-request"
# GTK treats a ``close-request`` handler returning True as "the window handled
# it, do not close". Sysbar always wants the default close to proceed.
_PROPAGATE_CLOSE = False


class PresentableWindow(Protocol):
    """The slice of ``Gtk.Window`` a slot needs."""

    def present(self) -> None: ...

    def connect(self, detailed_signal: str, handler: Callable[..., bool]) -> int: ...


W = TypeVar("W", bound=PresentableWindow)


class WindowSlot(Generic[W]):
    """Holds at most one live window, built on demand and dropped on close."""

    def __init__(
        self, factory: Callable[[], W], on_closed: Callable[[], None] | None = None
    ) -> None:
        self._factory = factory
        self._on_closed = on_closed
        self._window: W | None = None

    @property
    def is_open(self) -> bool:
        return self._window is not None

    def present(self) -> W:
        """Build the window if needed, bring it to the front, return it."""
        window = self._window
        if window is None:
            window = self._factory()
            window.connect(_CLOSE_REQUEST, self._on_close_request)
            self._window = window
        window.present()
        return window

    def if_open(self, action: Callable[[W], None]) -> None:
        """Run ``action`` on the live window, or do nothing if there is none."""
        window = self._window
        if window is not None:
            action(window)

    def forget(self) -> None:
        """Drop the reference without closing, so the next present rebuilds."""
        self._window = None

    def _on_close_request(self, *_args: object) -> bool:
        self._window = None
        if self._on_closed is not None:
            self._on_closed()
        return _PROPAGATE_CLOSE
