import os
import shutil
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


_PO_SOURCE = """msgid ""
msgstr "Content-Type: text/plain; charset=UTF-8\\n"

msgid "Start at login"
msgstr "Avvia all'accesso"
"""


def _write_catalog(locale_dir: Path) -> Path:
    messages = locale_dir / "it" / "LC_MESSAGES"
    messages.mkdir(parents=True)
    po = messages / "sysbar.po"
    po.write_text(_PO_SOURCE, encoding="utf-8")
    return po


def test_ensure_catalogs_compiled_creates_missing_mo(tmp_path: Path) -> None:
    if shutil.which("msgfmt") is None:
        pytest.skip("msgfmt not available")
    po = _write_catalog(tmp_path)
    localization._ensure_catalogs_compiled(tmp_path)
    assert po.with_suffix(".mo").exists()


def test_ensure_catalogs_compiled_recompiles_stale_mo(tmp_path: Path) -> None:
    if shutil.which("msgfmt") is None:
        pytest.skip("msgfmt not available")
    po = _write_catalog(tmp_path)
    mo = po.with_suffix(".mo")
    mo.write_bytes(b"stale")
    os.utime(mo, (0, 0))  # force the .mo older than the .po
    localization._ensure_catalogs_compiled(tmp_path)
    assert mo.read_bytes() != b"stale"


def test_ensure_catalogs_compiled_leaves_a_fresh_mo_alone(tmp_path: Path) -> None:
    """A catalogue newer than its source is not recompiled.

    Without this the branch was only exercised by whatever mtimes the checkout
    happened to have, which made its coverage depend on the working tree.
    """
    if shutil.which("msgfmt") is None:
        pytest.skip("msgfmt not available")
    po = _write_catalog(tmp_path)
    mo = po.with_suffix(".mo")
    mo.write_bytes(b"fresh")
    os.utime(po, (0, 0))  # force the .po older than the .mo

    localization._ensure_catalogs_compiled(tmp_path)

    assert mo.read_bytes() == b"fresh"


def test_ensure_catalogs_compiled_noop_without_msgfmt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    po = _write_catalog(tmp_path)
    monkeypatch.setattr("sysbar.core.localization.shutil.which", lambda _name: None)
    localization._ensure_catalogs_compiled(tmp_path)
    assert not po.with_suffix(".mo").exists()


def test_compile_catalog_logs_and_cleans_up_when_msgfmt_fails(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    po = tmp_path / "sysbar.po"
    po.write_text(_PO_SOURCE, encoding="utf-8")
    mo = po.with_suffix(".mo")
    tmp = mo.with_name(f"{mo.name}.tmp")

    # A missing compiler makes subprocess.run raise FileNotFoundError (an OSError):
    # the failure must be swallowed with a warning, leaving no partial output.
    with caplog.at_level("WARNING"):
        localization._compile_catalog(msgfmt="/nonexistent/msgfmt-binary", po=po, mo=mo)

    assert not mo.exists()
    assert not tmp.exists()
    assert "could not compile translation" in caplog.text


@pytest.mark.parametrize(
    ("source", "italian"),
    [
        ("Mute microphone", "Disattiva microfono"),
        ("Unmute microphone", "Riattiva microfono"),
        ("Turn on Do Not Disturb", "Attiva Non disturbare"),
        ("Switch to light mode", "Passa al tema chiaro"),
        ("Scenes", "Scene"),
        ("None", "Nessuna"),
        ("Clipboard", "Appunti"),
        ("Presentation", "Presentazione"),
        ("Power saving", "Risparmio energia"),
        ("End process", "Termina processo"),
    ],
)
def test_italian_catalog_translates_tray_and_dynamic_labels(source: str, italian: str) -> None:
    if shutil.which("msgfmt") is None:
        pytest.skip("msgfmt not available")
    localization.install_language("it")
    assert i18n._(source) == italian


def test_install_language_translates_after_on_demand_compile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if shutil.which("msgfmt") is None:
        pytest.skip("msgfmt not available")
    _write_catalog(tmp_path)
    monkeypatch.setattr(localization, "_LOCALE_CANDIDATES", (tmp_path,))
    localization.install_language("it")
    assert i18n._("Start at login") == "Avvia all'accesso"
