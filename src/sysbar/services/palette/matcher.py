"""Fuzzy matching and ranking for the palette.

Subsequence matching, so that "opcl" finds "Open clipboard history": every
character of the query must appear in order, not necessarily adjacent. Among the
entries that match, the ranking prefers matches that are contiguous, that start
words, and that start early, which is what makes a three-letter query land on
the row the user meant rather than on the first one alphabetically.

Pure and deterministic: no locale, no clock, no configuration. Ties are broken
by title so the order never wobbles between two identical runs.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable

from .models import PaletteEntry

# Characters after which the next one counts as starting a word.
_WORD_SEPARATORS = frozenset(" \t-_./:")

_SCORE_PER_CHARACTER = 1
# A contiguous run is the strongest signal, so its bonus must exceed the
# word-start one. Otherwise a query whose characters each happen to land on a
# word boundary ("o p e n" for "open") outscores the literal substring, since
# the word-start bonus is awarded once per character and accumulates.
_BONUS_CONSECUTIVE = 16
_BONUS_WORD_START = 10
_BONUS_FIRST_CHARACTER = 16
_PENALTY_PER_SKIPPED = 1
_MAX_LEADING_PENALTY = 20


def normalize(text: str) -> str:
    """Casefold and strip accents, so "però" is found by typing "pero"."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return stripped.casefold()


def score(query: str, text: str) -> int | None:
    """How well ``text`` matches ``query``, or ``None`` if it does not.

    An empty query matches everything with a score of zero, which lets the
    caller show a default listing without a separate code path.
    """
    needle, haystack = normalize(query), normalize(text)
    if not needle:
        return 0
    if len(needle) > len(haystack):
        return None
    return _greedy_score(needle, haystack)


def _greedy_score(needle: str, haystack: str) -> int | None:
    total = 0
    position = 0
    previous_index: int | None = None
    for character in needle:
        index = haystack.find(character, position)
        if index < 0:
            return None
        total += _SCORE_PER_CHARACTER + _position_bonus(haystack, index, previous_index)
        previous_index = index
        position = index + 1
    return total - min(_leading_penalty(haystack, needle), _MAX_LEADING_PENALTY)


def _position_bonus(haystack: str, index: int, previous_index: int | None) -> int:
    if previous_index is not None and index == previous_index + 1:
        return _BONUS_CONSECUTIVE
    if index == 0:
        return _BONUS_FIRST_CHARACTER
    if haystack[index - 1] in _WORD_SEPARATORS:
        return _BONUS_WORD_START
    return 0


def _leading_penalty(haystack: str, needle: str) -> int:
    """Discourage matches that only begin deep into the text."""
    first = haystack.find(needle[0])
    return max(first, 0) * _PENALTY_PER_SKIPPED


def rank(entries: Iterable[PaletteEntry], query: str, limit: int) -> list[PaletteEntry]:
    """The best ``limit`` entries for ``query``, best first.

    Runnable entries outrank unavailable ones with the same score: an entry the
    user cannot act on is worth showing, but never worth showing first.
    """
    scored: list[tuple[int, int, int, str, PaletteEntry]] = []
    for entry in entries:
        value = score(query, entry.haystack)
        if value is None:
            continue
        scored.append(
            (-value, 0 if entry.is_runnable else 1, -entry.weight, normalize(entry.title), entry)
        )
    scored.sort(key=lambda row: row[:4])
    return [row[4] for row in scored[:limit]]


def next_index(current: int, count: int, step: int) -> int:
    """Where an arrow key moves the selection, clamped to the list.

    Clamping rather than wrapping: a list that jumps from the last row back to
    the first on one more Down looks like the results changed under the user.
    ``current`` may be ``-1``, meaning nothing is selected yet, and ``count`` may
    be zero, in which case there is nowhere to go and ``-1`` comes back.
    """
    if count <= 0:
        return -1
    return max(0, min(count - 1, current + step))


def group_by_kind(entries: Iterable[PaletteEntry]) -> dict[str, list[PaletteEntry]]:
    """Bucket ranked entries by kind, preserving the ranking inside each bucket."""
    grouped: dict[str, list[PaletteEntry]] = {}
    for entry in entries:
        grouped.setdefault(entry.kind.value, []).append(entry)
    return grouped
