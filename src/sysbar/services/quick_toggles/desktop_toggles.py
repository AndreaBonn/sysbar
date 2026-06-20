"""Do-Not-Disturb and light/dark toggles over GNOME desktop GSettings.

Each toggle reads and flips one key in an external GNOME schema through an
injected :class:`GSettingsStore`, so the (small) interpretation logic — DND is
"banners off", dark is the ``prefer-dark`` scheme — is unit-tested with a fake
store instead of the live desktop.
"""

from __future__ import annotations

from ...core.constants import (
    COLOR_SCHEME_DARK,
    COLOR_SCHEME_DEFAULT,
    COLOR_SCHEME_KEY,
    SHOW_BANNERS_KEY,
)
from .ports import GSettingsStore


class DoNotDisturbToggle:
    """Suppresses notification banners (GNOME's Do Not Disturb)."""

    def __init__(self, store: GSettingsStore) -> None:
        self._store = store

    def is_active(self) -> bool:
        """DND is active when notification banners are turned off."""
        return not self._store.get_boolean(SHOW_BANNERS_KEY)

    def toggle(self) -> None:
        self._store.set_boolean(SHOW_BANNERS_KEY, self.is_active())


class ColorSchemeToggle:
    """Switches the desktop between the default and the dark colour scheme."""

    def __init__(self, store: GSettingsStore) -> None:
        self._store = store

    def is_dark(self) -> bool:
        return self._store.get_string(COLOR_SCHEME_KEY) == COLOR_SCHEME_DARK

    def toggle(self) -> None:
        self._store.set_string(
            COLOR_SCHEME_KEY, COLOR_SCHEME_DEFAULT if self.is_dark() else COLOR_SCHEME_DARK
        )
