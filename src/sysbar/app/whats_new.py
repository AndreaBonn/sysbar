"""What changed since the feature set a user last saw, for the post-update window.

The welcome stamps ``features-onboarding-version`` with the current feature set.
A user updated from an older set has a lower stamp: they get one short window
naming what is new and where to find it, then the stamp moves forward. Pure.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.constants import CURRENT_FEATURE_SET


@dataclass(frozen=True)
class Note:
    """One new thing, said in a line, with where to find it."""

    feature_set: int
    title: str
    detail: str
    icon_name: str


NOTES: tuple[Note, ...] = (
    Note(
        5,
        "Command palette",
        "Search every action, scene and clipboard entry. Right-click the icon, "
        "then Search commands…",
        "system-search-symbolic",
    ),
    Note(
        5,
        "Scenes",
        "Change several things with one click: right-click the icon, then Scenes or Manage scenes…",
        "starred-symbolic",
    ),
    Note(
        5,
        "A panel that tells you how things are",
        "A summary line and quick toggles at the top of the panel.",
        "utilities-system-monitor-symbolic",
    ),
    Note(
        5,
        "Preferences that explain themselves",
        "Each feature says what it does, and alerts come with a limit already set.",
        "emblem-system-symbolic",
    ),
    Note(
        5,
        "Undo",
        "Clearing the clipboard or the shelf can be undone for a few seconds.",
        "edit-undo-symbolic",
    ),
)


def notes_since(*, seen: int, current: int = CURRENT_FEATURE_SET) -> tuple[Note, ...]:
    """Notes newer than the feature set ``seen``, up to ``current``."""
    return tuple(note for note in NOTES if seen < note.feature_set <= current)


def should_show_whats_new(*, onboarded: bool, seen: int) -> bool:
    """Only for users updated past the set they saw; a first run gets the welcome."""
    return onboarded and bool(notes_since(seen=seen))
