"""The command palette: its window, and the search behind it.

The entries are supplied as a callable rather than held, because the palette
lists things that change while it is closed. Calling it on every keystroke also
means there is no cache to invalidate and no staleness to reason about; the cost
is a list rebuild per keystroke over a set measured in dozens of rows.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ...core.constants import PALETTE_MAX_RESULTS
from ...services.palette.matcher import rank
from ...services.palette.models import PaletteEntry
from ..windows import WindowSlot

if TYPE_CHECKING:
    from ...ui.palette.palette_window import PaletteWindow

EntrySource = Callable[[], list[PaletteEntry]]


class PaletteFeature:
    """Owns the palette window and ranks the entries it shows."""

    def __init__(self, entries: EntrySource) -> None:
        self._entries = entries
        self._window: WindowSlot[PaletteWindow] = WindowSlot(self._build_window)

    def open(self) -> None:
        self._window.present()

    def search(self, query: str) -> list[PaletteEntry]:
        """The best matches for ``query``, read from the features as they are now."""
        return rank(self._entries(), query, PALETTE_MAX_RESULTS)

    def _build_window(self) -> PaletteWindow:
        from ...ui.palette.palette_window import PaletteWindow

        return PaletteWindow(self.search)
