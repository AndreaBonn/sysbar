"""Interface for global shortcuts.

The manager depends only on this protocol; the xdg-desktop-portal client is the
concrete implementation. Tests inject a fake, so the enable/bind decision runs
without a portal.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


class GlobalShortcuts(Protocol):
    """Registers a global shortcut and reports its activation."""

    def bind(
        self, shortcut_id: str, description: str, on_activated: Callable[[], None]
    ) -> None: ...
