"""The welcome window on first run or on request, and the what's-new window after an update."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.constants import CURRENT_FEATURE_SET
from ..context import AppContext
from ..whats_new import notes_since, should_show_whats_new
from ..windows import WindowSlot

if TYPE_CHECKING:
    from ...ui.onboarding.onboarding_window import OnboardingWindow
    from ...ui.onboarding.whats_new_window import WhatsNewWindow

_ONBOARDED_KEY = "has-onboarded"
_FEATURE_SET_KEY = "features-onboarding-version"


class OnboardingFeature:
    """Owns the welcome window and the "already onboarded" bookkeeping."""

    def __init__(self, context: AppContext) -> None:
        self._context = context
        self._window: WindowSlot[OnboardingWindow] = WindowSlot(self._build_window)
        self._whats_new: WindowSlot[WhatsNewWindow] = WindowSlot(self._build_whats_new)

    def show_if_first_run(self) -> None:
        """The welcome on a first run; after an update, what changed (O7).

        The set counts as seen only once the what's-new window is closed: if the
        app stops while it is still open, it comes back on the next launch rather
        than being lost unread.
        """
        config = self._context.config
        onboarded = config.get_bool(_ONBOARDED_KEY)
        if not onboarded:
            self.show()
        elif should_show_whats_new(onboarded=onboarded, seen=self._seen_set()):
            self._whats_new.present()

    def _seen_set(self) -> int:
        return int(self._context.config.settings.get_int(_FEATURE_SET_KEY))

    def _build_whats_new(self) -> WhatsNewWindow:
        from ...ui.onboarding.whats_new_window import WhatsNewWindow

        return WhatsNewWindow(notes_since(seen=self._seen_set()), on_seen=self._mark_seen)

    def _mark_seen(self) -> None:
        self._context.config.settings.set_int(_FEATURE_SET_KEY, CURRENT_FEATURE_SET)

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
        self._mark_seen()
