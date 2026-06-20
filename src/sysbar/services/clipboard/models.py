"""Clipboard history entry model and its JSON serialization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ...core.constants import CLIP_LABEL_MAX, URL_PREFIXES


class ClipKind(StrEnum):
    """The kind of content captured from the clipboard."""

    TEXT = "text"
    URL = "url"


def classify(text: str) -> ClipKind:
    """Classify clipboard text as a URL or plain text."""
    return ClipKind.URL if text.startswith(URL_PREFIXES) else ClipKind.TEXT


def make_label(text: str) -> str:
    """Return a single-line, length-capped label for a clipboard entry."""
    collapsed = " ".join(text.split())
    return collapsed[:CLIP_LABEL_MAX] or "text"


@dataclass(frozen=True)
class ClipEntry:
    """One clipboard history entry."""

    id: str
    kind: ClipKind
    text: str
    label: str
    pinned: bool = False

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "text": self.text,
            "label": self.label,
            "pinned": self.pinned,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | bool]) -> ClipEntry:
        return cls(
            id=str(data["id"]),
            kind=ClipKind(str(data["kind"])),
            text=str(data["text"]),
            label=str(data["label"]),
            pinned=bool(data.get("pinned", False)),
        )
