"""Localization via gettext.

Two languages are shipped (``it``, ``en``); ``en`` is the fallback. An empty
configured language means "follow the system locale". Adding a language only
requires shipping a new ``.po``/``.mo``: no code change.
"""

from __future__ import annotations

import gettext
import os
from pathlib import Path

from . import i18n
from .constants import GETTEXT_DOMAIN

SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "it")
FALLBACK_LANGUAGE = "en"

# In an installed package this resolves to /usr/share/locale; in a source
# checkout to data/locale. Both are tried, first existing wins.
_LOCALE_CANDIDATES = (
    Path(__file__).resolve().parents[3] / "data" / "locale",
    Path("/usr/share/locale"),
)


def _locale_dir() -> Path:
    for candidate in _LOCALE_CANDIDATES:
        if candidate.is_dir():
            return candidate
    return _LOCALE_CANDIDATES[-1]


def install_language(language: str = "") -> str:
    """Install the gettext ``_`` builtin for the requested language.

    Parameters
    ----------
    language
        Language code, or empty string to follow the system locale.

    Returns
    -------
    str
        The language code that was actually installed.
    """
    resolved = language or _system_language()
    translation = gettext.translation(
        GETTEXT_DOMAIN,
        localedir=str(_locale_dir()),
        languages=[resolved, FALLBACK_LANGUAGE],
        fallback=True,
    )
    i18n.set_translation(translation)
    return resolved


def _system_language() -> str:
    raw = os.environ.get("LANG", "") or os.environ.get("LC_ALL", "")
    code = raw.split(".", 1)[0].split("_", 1)[0]
    return code if code in SUPPORTED_LANGUAGES else FALLBACK_LANGUAGE
