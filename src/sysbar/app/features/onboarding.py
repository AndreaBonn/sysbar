"""The welcome window: shown on first run, and again on request from Preferences."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.constants import CURRENT_FEATURE_SET
from ..context import AppContext
from ..windows import WindowSlot

if TYPE_CHECKING:
    from ...ui.onboarding.onboarding_window import OnboardingWindow

_ONBOARDED_KEY = "has-onboarded"
_FEATURE_SET_KEY = "features-onboarding-version"


class OnboardingFeature:
    """Owns the welcome window and the "already onboarded" bookkeeping."""

    def __init__(self, context: AppContext) -> None:
        self._context = context
        self._window: WindowSlot[OnboardingWindow] = WindowSlot(self._build_window)

    def show_if_first_run(self) -> None:
        if not self._context.config.get_bool(_ONBOARDED_KEY):
            self.show()

    def show(self) -> None:
        """Open the welcome now, or raise it if it is already open."""
        self._window.present()

    def _build_window(self) -> OnboardingWindow:
        from ...ui.onboarding.onboarding_window import OnboardingWindow

        return OnboardingWindow(
            self._context.capabilities,
            config=self._context.config,
            autostart=self._context.autostart,
            on_finish=self._finish,
        )

    def _finish(self) -> None:
        config = self._context.config
        config.set_bool(_ONBOARDED_KEY, True)
        config.settings.set_int(_FEATURE_SET_KEY, CURRENT_FEATURE_SET)
