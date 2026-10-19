"""What the command palette shows and decides, kept free of GTK.

The window places rows and reacts to keys; which action Enter takes, how a
row reads and which section header it opens are decided here, so they can be
tested without a display.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from ..core.i18n import _
from ..services.palette.models import EntryKind, PaletteEntry

_KIND_VALUES = frozenset(kind.value for kind in EntryKind)
# K2: a section title per kind (the window adds the matching icon), so a masked
# clip never passes for a command.
_KIND_TITLES = {
    EntryKind.COMMAND: "Actions",
    EntryKind.TOGGLE: "Quick toggles",
    EntryKind.SCENE: "Scenes",
    EntryKind.CLIPBOARD: "Clipboard",
    EntryKind.SHELF: "Shelf",
    EntryKind.DEVICE: "Audio devices",
}


class RunDecision(Enum):
    """What Enter does on a row: run it, apply its fix, or nothing."""

    RUN = auto()
    FIX = auto()
    IGNORE = auto()


@dataclass(frozen=True)
class RowPresentation:
    """How one result row reads and which buttons it carries."""

    subtitle: str
    activatable: bool
    dimmed: bool
    show_reveal: bool
    show_fix: bool


def run_decision(entry: PaletteEntry) -> RunDecision:
    """Choose an action without invoking the entry or its fix."""
    if entry.is_runnable:
        return RunDecision.RUN
    if entry.fix_label:
        return RunDecision.FIX
    return RunDecision.IGNORE


def section_title(kind_value: str, previous_kind_value: str | None) -> str | None:
    """Return the translated heading when a known kind starts a section."""
    # The kind travels on the row (its widget name): GTK also calls this while
    # remove_all() tears the old rows down, when self._rows already holds the
    # new results and an index into it would be wrong or out of range.
    if kind_value == previous_kind_value or kind_value not in _KIND_VALUES:
        return None
    return _(_KIND_TITLES[EntryKind(kind_value)])


def row_presentation(entry: PaletteEntry) -> RowPresentation:
    """Derive the text, activation and affordances of a palette row."""
    # A dead end reads dimmed; a row with a fix stays at full strength so its
    # button does not look disabled too.
    return RowPresentation(
        subtitle=entry.unavailable_reason or entry.subtitle,
        activatable=entry.is_runnable,
        dimmed=not entry.is_runnable and not entry.fix_label,
        show_reveal=entry.masked,
        show_fix=bool(entry.fix_label),
    )


def empty_state(query: str) -> tuple[str, str]:
    """K5: name the query, and say what the palette can find."""
    title = _("Nothing matches “{query}”").format(query=query) if query else _("No matches")
    description = _(
        "The palette finds Sysbar's own actions, scenes, clipboard "
        "entries and audio devices. Try “mic”, “dark” or “focus”."
    )
    return title, description
