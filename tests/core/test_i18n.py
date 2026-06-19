import gettext
from collections.abc import Iterator

import pytest

from sysbar.core import i18n


class _FakeTranslation(gettext.NullTranslations):
    def gettext(self, message: str) -> str:
        return {"Settings": "Impostazioni"}.get(message, message)


@pytest.fixture(autouse=True)
def _restore_translation() -> Iterator[None]:
    saved = i18n._translation
    yield
    i18n.set_translation(saved)


def test_underscore_falls_back_to_msgid_by_default() -> None:
    i18n.set_translation(gettext.NullTranslations())
    assert i18n._("Settings") == "Settings"


def test_underscore_uses_active_translation() -> None:
    i18n.set_translation(_FakeTranslation())
    assert i18n._("Settings") == "Impostazioni"
    assert i18n._("Unknown") == "Unknown"


def test_set_translation_can_be_rebound() -> None:
    i18n.set_translation(_FakeTranslation())
    i18n.set_translation(gettext.NullTranslations())
    assert i18n._("Settings") == "Settings"
