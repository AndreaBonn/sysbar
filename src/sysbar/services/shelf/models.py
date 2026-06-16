"""Shelf item model and its JSON serialization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


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
