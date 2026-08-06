"""A heuristic for clipboard text that is probably a credential.

The clipboard history is stored in plain text and the README says so. That is a
rate-limited exposure today: an entry is visible only to someone who opens the
history window. A palette searchable from a global shortcut widens it, because a
screen recording, a screenshot tool or a shared screen then catches a scrollable
list of past secrets instead of a single value.

This module does not fix the storage, which is a separate debt. It decides which
entries the palette shows masked until the user asks to see them.

It is a heuristic and it is wrong in both directions: a passphrase made of
ordinary words is missed, and a long random-looking identifier is masked for no
reason. It is tuned to over-mask rather than under-mask, because the cost of the
two mistakes is not symmetric.
"""

from __future__ import annotations

import re

# Vendor prefixes that identify a credential on sight. Cheap and exact, so they
# are checked before the entropy heuristic.
_SECRET_PREFIXES: tuple[str, ...] = (
    "ghp_",
    "gho_",
    "ghu_",
    "ghs_",
    "ghr_",
    "github_pat_",
    "glpat-",
    "sk-",
    "sk_live_",
    "pk_live_",
    "rk_live_",
    "xoxb-",
    "xoxp-",
    "xoxa-",
    "xoxr-",
    "AKIA",
    "ASIA",
    "AIza",
    "ya29.",
    "hf_",
    "sbp_",
    "dop_v1_",
    "npm_",
)

# A JWT: three base64url segments, the first of which encodes ``{"``.
_JWT = re.compile(r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*$")

# A URL carrying credentials in its query string.
_URL_SECRET = re.compile(r"[?&](token|api_?key|access_?token|password|secret)=", re.IGNORECASE)

# A single opaque token: no whitespace, long, and drawn from an alphabet that
# suggests it was generated rather than typed.
_OPAQUE = re.compile(r"^[A-Za-z0-9+/=_.\-]+$")
_MIN_OPAQUE_LENGTH = 24
_MIN_CHARACTER_CLASSES = 3

# A filesystem path satisfies the opaque-token rule: long, no whitespace, and
# mixed character classes as soon as it has capitals and an extension. Copying a
# path is far more common than copying a secret that starts with a slash, so
# paths are excluded rather than masked.
_PATH_PREFIXES: tuple[str, ...] = ("/", "./", "../", "~/")


def looks_like_secret(text: str) -> bool:
    """Whether ``text`` should be masked until the user asks to see it."""
    candidate = text.strip()
    if not candidate:
        return False
    if candidate.startswith(_SECRET_PREFIXES):
        return True
    if _JWT.match(candidate):
        return True
    if _URL_SECRET.search(candidate):
        return True
    return _is_opaque_token(candidate)


def _is_opaque_token(candidate: str) -> bool:
    """A long single token mixing character classes, with no whitespace.

    A URL never reaches the class count: ``:`` is not in the token alphabet, so
    it fails the pattern above. Only paths need excluding explicitly.
    """
    if len(candidate) < _MIN_OPAQUE_LENGTH or not _OPAQUE.match(candidate):
        return False
    if candidate.startswith(_PATH_PREFIXES):
        return False
    return _character_classes(candidate) >= _MIN_CHARACTER_CLASSES


def _character_classes(candidate: str) -> int:
    return sum(
        (
            any(character.islower() for character in candidate),
            any(character.isupper() for character in candidate),
            any(character.isdigit() for character in candidate),
            any(character in "+/=_.-" for character in candidate),
        )
    )


def mask(text: str, visible: int = 4) -> str:
    """A display form that shows only the first few characters."""
    stripped = " ".join(text.split())
    if len(stripped) <= visible:
        return "•" * len(stripped)
    return stripped[:visible] + "•" * min(len(stripped) - visible, 12)
