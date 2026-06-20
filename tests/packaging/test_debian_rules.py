"""Regression guard for the Debian packaging install rules.

The gettext catalog lookup requires the per-language directory level to survive
installation: ``/usr/share/locale/<lang>/LC_MESSAGES/sysbar.mo``. A previous
version copied ``data/locale/*`` into a destination that did not yet exist; with
a single language directory as the source, ``cp`` renamed ``it/`` to ``locale/``,
flattening the language level and making the app fall back to English.
"""

from __future__ import annotations

from pathlib import Path

_RULES = Path(__file__).resolve().parents[2] / "packaging" / "debian" / "rules"


def _rules_text() -> str:
    return _RULES.read_text(encoding="utf-8")


def test_locale_destination_is_created_before_copy() -> None:
    text = _rules_text()
    create_idx = text.find("install -d $(PKG)/usr/share/locale")
    copy_idx = text.find("cp -r data/locale/*")
    assert create_idx != -1, "rules must create the locale destination explicitly"
    assert copy_idx != -1, "rules must copy the locale catalogs"
    assert create_idx < copy_idx, "the destination must exist before the copy runs"


def test_source_locale_keeps_the_language_directory_level() -> None:
    locale_root = _RULES.resolve().parents[2] / "data" / "locale"
    catalogs = list(locale_root.rglob("*.po"))
    assert catalogs, "expected at least one shipped translation catalog"
    for po in catalogs:
        # data/locale/<lang>/LC_MESSAGES/<domain>.po
        assert po.parent.name == "LC_MESSAGES"
        lang = po.parent.parent.name
        assert lang and lang != "locale", f"unexpected language directory: {lang}"
