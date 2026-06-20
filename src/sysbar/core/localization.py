"""Localization via gettext.

Two languages are shipped (``it``, ``en``); ``en`` is the fallback. An empty
configured language means "follow the system locale". Adding a language only
requires shipping a new ``.po``/``.mo``: no code change.

When running from a source checkout the binary ``.mo`` catalogs are not present
(they are git-ignored build artifacts). To make translations work without a full
``build.sh`` run, missing or stale ``.mo`` files are compiled on demand from the
neighbouring ``.po`` via ``msgfmt`` when that tool is available.
"""

from __future__ import annotations

import gettext
import logging
import os
import shutil
import subprocess
from pathlib import Path

from . import i18n
from .constants import GETTEXT_DOMAIN

log = logging.getLogger(__name__)

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
    locale_dir = _locale_dir()
    _ensure_catalogs_compiled(locale_dir)
    translation = gettext.translation(
        GETTEXT_DOMAIN,
        localedir=str(locale_dir),
        languages=[resolved, FALLBACK_LANGUAGE],
        fallback=True,
    )
    i18n.set_translation(translation)
    return resolved


def _system_language() -> str:
    raw = os.environ.get("LANG", "") or os.environ.get("LC_ALL", "")
    code = raw.split(".", 1)[0].split("_", 1)[0]
    return code if code in SUPPORTED_LANGUAGES else FALLBACK_LANGUAGE


def _ensure_catalogs_compiled(locale_dir: Path) -> None:
    """Compile every ``.po`` whose ``.mo`` is missing or stale.

    No-op when ``msgfmt`` is unavailable: gettext then falls back to the source
    strings, which is the pre-existing behaviour.
    """
    msgfmt = shutil.which("msgfmt")
    if msgfmt is None:
        return
    for po in locale_dir.rglob("*.po"):
        mo = po.with_suffix(".mo")
        if _is_fresh(mo=mo, po=po):
            continue
        _compile_catalog(msgfmt=msgfmt, po=po, mo=mo)


def _is_fresh(mo: Path, po: Path) -> bool:
    return mo.exists() and mo.stat().st_mtime >= po.stat().st_mtime


def _compile_catalog(msgfmt: str, po: Path, mo: Path) -> None:
    """Compile ``po`` into ``mo`` atomically, logging instead of raising on failure."""
    tmp = mo.with_name(f"{mo.name}.tmp")
    try:
        subprocess.run(
            [msgfmt, str(po), "-o", str(tmp)],
            check=True,
            capture_output=True,
        )
        tmp.replace(mo)
    except (OSError, subprocess.CalledProcessError) as err:
        tmp.unlink(missing_ok=True)
        log.warning("could not compile translation %s: %s", po.name, err)
