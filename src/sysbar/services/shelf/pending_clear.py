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
    """Manage the batch detached by the latest shelf clear.

    Each clear opens a numbered batch. A toast acts only on its own batch:
    the overlay queues a second toast behind the first, so the first one
    times out (or is undone) while a later clear is the one pending.
    """

    def __init__(self, service: ShelfService) -> None:
        self._service = service
        self._pending: list[ShelfItem] = []
        self._batch = 0

    def clear(self) -> int | None:
        """Commit the previous batch and detach the current shelf for undo.

        Returns the number of the new batch, or ``None`` when the shelf was
        already empty and no toast is due.
        """
        self.commit()
        detached = self._service.detach_all()
        if not detached:
            return None
        self._batch += 1
        self._pending = detached
        return self._batch

    def undo(self, *, batch: int | None = None) -> None:
        """Restore the pending batch ahead of any newly added items.

        With ``batch``, only that batch: a superseded one was already
        committed by the clear that followed it.
        """
        if not self._is_current(batch):
            return
        pending, self._pending = self._pending, []
        self._service.restore(items=pending)

    def commit(self, *, batch: int | None = None) -> None:
        """Delete what the last clear detached, unless it was undone.

        Called when the toast goes away, before a second clear and when the
        window closes; whatever slips past (the app killed mid-toast) is pruned
        from staging at the next load. With ``batch``, only that batch, so a
        toast timing out never deletes the batch of a later clear.
        """
        if not self._is_current(batch):
            return
        pending, self._pending = self._pending, []
        if pending:
            self._service.discard(items=pending)

    def _is_current(self, batch: int | None) -> bool:
        return batch is None or batch == self._batch
