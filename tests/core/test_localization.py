from collections.abc import Iterator
from pathlib import Path

import pytest

from sysbar.core import i18n, localization


@pytest.fixture(autouse=True)
def _restore_translation() -> Iterator[None]:
    saved = i18n._translation
    yield
    i18n.set_translation(saved)


def test_system_language_parses_lang_country_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANG", "it_IT.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    assert localization._system_language() == "it"


def test_system_language_unsupported_falls_back_to_english(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANG", "de_DE.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    assert localization._system_language() == localization.FALLBACK_LANGUAGE


def test_system_language_unset_falls_back_to_english(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)
    assert localization._system_language() == "en"


def test_system_language_uses_lc_all_when_lang_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANG", "")
    monkeypatch.setenv("LC_ALL", "it_IT.UTF-8")
    assert localization._system_language() == "it"


def test_install_language_returns_requested_code() -> None:
    assert localization.install_language("it") == "it"


def test_install_language_empty_follows_system_locale(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANG", "it_IT.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    assert localization.install_language("") == "it"


def test_install_language_rebinds_active_translation() -> None:
    localization.install_language("en")
    # NullTranslations / missing catalog falls back to the source string.
    assert i18n._("Keep awake") == "Keep awake"


def test_locale_dir_returns_an_existing_or_fallback_candidate() -> None:
    result = localization._locale_dir()
    assert isinstance(result, Path)
    assert result in localization._LOCALE_CANDIDATES


def test_locale_dir_uses_fallback_when_no_candidate_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = (Path("/nonexistent/a"), Path("/nonexistent/b"))
    monkeypatch.setattr(localization, "_LOCALE_CANDIDATES", fake)
    assert localization._locale_dir() == fake[-1]
