"""Shelf item model and its JSON serialization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ItemKind(StrEnum):
    """The kind of content held in a shelf tile."""

    FILE = "file"
    IMAGE = "image"
    TEXT = "text"
    URL = "url"


@dataclass(frozen=True)
class ShelfItem:
    """One item on the shelf.

    ``path`` is set for file/image items (a real path or a staged copy);
    ``text`` is set for text/url items.
    """

    id: str
    kind: ItemKind
    label: str
    path: str | None = None
    text: str | None = None

    @property
    def open_uri(self) -> str | None:
        """URI to open with the default app, or ``None`` if not openable.

        File and image items resolve to a ``file://`` URI; URL items return
        their stored URL. Plain text items, and file/image items without an
        absolute path, have no openable target.
        """
        if self.kind in (ItemKind.FILE, ItemKind.IMAGE) and self.path:
            file = Path(self.path)
            return file.as_uri() if file.is_absolute() else None
        if self.kind is ItemKind.URL:
            return self.text
        return None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "label": self.label,
            "path": self.path,
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | None]) -> ShelfItem:
        return cls(
            id=str(data["id"]),
            kind=ItemKind(str(data["kind"])),
            label=str(data["label"]),
            path=data.get("path"),
            text=data.get("text"),
        )
