"""Shelf service: holds items, stages volatile content and persists a manifest.

Files are kept by reference; volatile content (dropped images, text from other
apps) is copied into a staging directory. The manifest is a JSON list. The data
directory and id factory are injected so persistence is unit-tested.
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

from ...core.i18n import _  # noqa: E402
from .models import ItemKind, ShelfItem  # noqa: E402

log = logging.getLogger(__name__)

_MANIFEST_NAME = "manifest.json"
_STAGING_NAME = "staging"
_TEXT_LABEL_MAX = 40
_URL_SCHEMES = ("http://", "https://", "ftp://")


class ShelfService(GObject.Object):
    """Manages shelf items and their persistence."""

    __gsignals__: ClassVar[dict[str, tuple[object, ...]]] = {
        "items-changed": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, data_dir: Path, id_factory: Callable[[], str] | None = None) -> None:
        super().__init__()
        self._data_dir = data_dir
        self._staging = data_dir / _STAGING_NAME
        self._manifest = data_dir / _MANIFEST_NAME
        self._id_factory = id_factory or (lambda: uuid4().hex)
        self._items: list[ShelfItem] = []

    @property
    def items(self) -> list[ShelfItem]:
        return list(self._items)

    def add_file(self, path: str) -> ShelfItem:
        item = ShelfItem(
            id=self._id_factory(), kind=ItemKind.FILE, label=Path(path).name, path=path
        )
        return self._append(item)

    def add_url(self, url: str) -> ShelfItem:
        return self._append(
            ShelfItem(id=self._id_factory(), kind=ItemKind.URL, label=url, text=url)
        )

    def add_text(self, text: str) -> ShelfItem:
        label = text.strip().replace("\n", " ")[:_TEXT_LABEL_MAX] or _("text")
        return self._append(
            ShelfItem(id=self._id_factory(), kind=ItemKind.TEXT, label=label, text=text)
        )

    def add_dropped_text(self, value: str) -> ShelfItem:
        """Classify dropped text by the URL schemes accepted by the shelf."""
        if value.startswith(_URL_SCHEMES):
            return self.add_url(url=value)
        return self.add_text(text=value)

    def add_image(self, data: bytes, suffix: str = ".png") -> ShelfItem:
        self._staging.mkdir(parents=True, exist_ok=True)
        item_id = self._id_factory()
        staged = self._staging / f"{item_id}{suffix}"
        staged.write_bytes(data)
        return self._append(
            ShelfItem(id=item_id, kind=ItemKind.IMAGE, label=_("Image"), path=str(staged))
        )

    def remove(self, item_id: str) -> None:
        item = next((i for i in self._items if i.id == item_id), None)
        if item is None:
            return
        self._items = [i for i in self._items if i.id != item_id]
        self._discard_staged(item)
        self.save()
        self.emit("items-changed")

    def clear(self) -> None:
        for item in self._items:
            self._discard_staged(item)
        self._items = []
        self.save()
        self.emit("items-changed")

    def detach_all(self) -> list[ShelfItem]:
        """Empty the shelf but keep staged copies, so the clear can be undone.

        Pair with :meth:`restore` (undo) or :meth:`discard` (commit).
        """
        detached = self._items
        self._items = []
        self.save()
        self.emit("items-changed")
        return detached

    def restore(self, items: list[ShelfItem]) -> None:
        """Put detached items back first, ahead of anything dropped since."""
        present = {item.id for item in self._items}
        self._items = [item for item in items if item.id not in present] + self._items
        self.save()
        self.emit("items-changed")

    def discard(self, items: list[ShelfItem]) -> None:
        """Delete the staged copies of detached items that were not restored."""
        present = {item.id for item in self._items}
        for item in items:
            if item.id not in present:
                self._discard_staged(item)

    def load(self) -> None:
        if not self._manifest.is_file():
            return
        try:
            raw = json.loads(self._manifest.read_text(encoding="utf-8"))
            self._items = [ShelfItem.from_dict(entry) for entry in raw]
        except (OSError, ValueError, KeyError):
            log.warning("could not read shelf manifest", extra={"path": str(self._manifest)})
            self._items = []
        else:
            self._prune_staging()
        self.emit("items-changed")

    def _prune_staging(self) -> None:
        """Delete staged copies no item refers to.

        A clear held for undo saves the manifest at once but deletes staged
        files only when committed; if the app stops in between, they would stay
        on disk forever. Runs only after a manifest read cleanly, so a corrupt
        manifest never empties the staging directory.
        """
        if not self._staging.is_dir():
            return
        referenced = {item.path for item in self._items if item.path}
        for staged in self._staging.iterdir():
            if str(staged) not in referenced:
                staged.unlink(missing_ok=True)

    def save(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        payload = [item.to_dict() for item in self._items]
        self._manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _append(self, item: ShelfItem) -> ShelfItem:
        self._items.append(item)
        self.save()
        self.emit("items-changed")
        return item

    def _discard_staged(self, item: ShelfItem) -> None:
        if item.kind is ItemKind.IMAGE and item.path:
            staged = Path(item.path)
            if staged.parent == self._staging:
                staged.unlink(missing_ok=True)
