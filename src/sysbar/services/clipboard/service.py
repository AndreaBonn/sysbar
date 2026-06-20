"""Clipboard history service: a deduped, pinnable, persisted ring buffer.

Mirrors the shelf's persistence shape (a JSON manifest, an injected id factory,
an ``items-changed`` signal) but holds clipboard captures. Re-capturing existing
text moves it to the front instead of duplicating; pinned entries survive both
ring-buffer eviction and ``clear``. The logic is framework-agnostic and
unit-tested; the live clipboard listener is a separate boundary.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar
from uuid import uuid4

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GObject  # noqa: E402

from ...core.constants import CLIPBOARD_MAX_ENTRIES  # noqa: E402
from .models import ClipEntry, classify, make_label  # noqa: E402

log = logging.getLogger(__name__)

_MANIFEST_NAME = "manifest.json"


class ClipboardService(GObject.Object):
    """Holds clipboard history and persists it to a manifest."""

    __gsignals__: ClassVar[dict[str, tuple[object, ...]]] = {
        "items-changed": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(
        self,
        data_dir: Path,
        max_entries: int = CLIPBOARD_MAX_ENTRIES,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        super().__init__()
        self._data_dir = data_dir
        self._manifest = data_dir / _MANIFEST_NAME
        self._max_entries = max_entries
        self._id_factory = id_factory or (lambda: uuid4().hex)
        self._entries: list[ClipEntry] = []

    @property
    def items(self) -> list[ClipEntry]:
        """Entries with pinned ones first, each group most-recent first."""
        pinned = [entry for entry in self._entries if entry.pinned]
        unpinned = [entry for entry in self._entries if not entry.pinned]
        return pinned + unpinned

    def capture(self, text: str) -> ClipEntry | None:
        """Record clipboard ``text`` at the front, or ``None`` if blank.

        Re-capturing identical text moves the existing entry to the front,
        preserving its pinned state, rather than creating a duplicate.
        """
        cleaned = text.strip()
        if not cleaned:
            return None
        existing = next((e for e in self._entries if e.text == cleaned), None)
        if existing is not None:
            self._entries.remove(existing)
            entry = existing
        else:
            entry = ClipEntry(
                id=self._id_factory(),
                kind=classify(cleaned),
                text=cleaned,
                label=make_label(cleaned),
            )
        self._entries.insert(0, entry)
        self._evict()
        self._commit()
        return entry

    def toggle_pin(self, entry_id: str) -> None:
        self._replace(entry_id, lambda e: ClipEntry(e.id, e.kind, e.text, e.label, not e.pinned))

    def remove(self, entry_id: str) -> None:
        self._entries = [e for e in self._entries if e.id != entry_id]
        self._commit()

    def clear(self) -> None:
        """Drop every unpinned entry, keeping pinned ones."""
        self._entries = [e for e in self._entries if e.pinned]
        self._commit()

    def search(self, query: str) -> list[ClipEntry]:
        """Return entries whose text contains ``query`` (case-insensitive)."""
        needle = query.strip().lower()
        if not needle:
            return self.items
        return [entry for entry in self.items if needle in entry.text.lower()]

    def load(self) -> None:
        if not self._manifest.is_file():
            return
        try:
            raw = json.loads(self._manifest.read_text(encoding="utf-8"))
            self._entries = [ClipEntry.from_dict(entry) for entry in raw]
        except (OSError, ValueError, KeyError):
            log.warning("could not read clipboard manifest", extra={"path": str(self._manifest)})
            self._entries = []
        self.emit("items-changed")

    def save(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        payload = [entry.to_dict() for entry in self._entries]
        self._manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _evict(self) -> None:
        """Trim to the size cap by dropping the oldest unpinned entries."""
        while len(self._entries) > self._max_entries:
            oldest_unpinned = next((e for e in reversed(self._entries) if not e.pinned), None)
            if oldest_unpinned is None:
                return
            self._entries.remove(oldest_unpinned)

    def _replace(self, entry_id: str, transform: Callable[[ClipEntry], ClipEntry]) -> None:
        self._entries = [transform(e) if e.id == entry_id else e for e in self._entries]
        self._commit()

    def _commit(self) -> None:
        self.save()
        self.emit("items-changed")
