"""Translation entry point.

UI modules import ``_`` from here. It delegates to the translation installed at
startup, so it is statically resolvable (no implicit ``builtins._``) and the
language can be switched at runtime by rebinding the translation.
"""

from __future__ import annotations

import gettext as _gettext

_translation: _gettext.NullTranslations = _gettext.NullTranslations()


def set_translation(translation: _gettext.NullTranslations) -> None:
    """Rebind the active translation (called by :mod:`sysbar.core.localization`)."""
    global _translation
    _translation = translation


def _(message: str) -> str:
    """Translate ``message`` using the active translation."""
    return _translation.gettext(message)
