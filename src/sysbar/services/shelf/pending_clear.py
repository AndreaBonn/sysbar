"""The undo window of "Clear shelf" (S2).

A clear detaches every item but deletes nothing until the toast goes away, so
the user can take it back. Which batch is pending, when it is finally deleted
and what undo restores is decided here, testable against a real
:class:`ShelfService`; the window only shows the toast.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import ShelfItem

if TYPE_CHECKING:
    from .shelf_service import ShelfService


class PendingClear:
    """Manage the batch detached by the latest shelf clear."""

    def __init__(self, service: ShelfService) -> None:
        self._service = service
        self._pending: list[ShelfItem] = []

    def clear(self) -> bool:
        """Commit the previous batch and detach the current shelf for undo."""
        self.commit()
        detached = self._service.detach_all()
        if not detached:
            return False
        self._pending = detached
        return True

    def undo(self) -> None:
        """Restore the pending batch ahead of any newly added items."""
        pending, self._pending = self._pending, []
        self._service.restore(items=pending)

    def commit(self) -> None:
        """Delete what the last clear detached, unless it was undone.

        Called when the toast goes away, before a second clear and when the
        window closes; whatever slips past (the app killed mid-toast) is pruned
        from staging at the next load.
        """
        pending, self._pending = self._pending, []
        if pending:
            self._service.discard(items=pending)
