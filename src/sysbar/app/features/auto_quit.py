"""Auto-quit, plus the choice of window source for the running session.

Window tracking comes from libwnck on X11 and from the bundled GNOME Shell
extension on Wayland. With neither available the feature stays off: that is a
degraded session, not an error, so it is logged and the application carries on.
"""

from __future__ import annotations

import logging

from ...core.capabilities import SESSION_X11, WAYLAND_WINDOW_SOURCE
from ...core.constants import AUTO_QUIT_SYSTEM_WHITELIST
from ...services.auto_quit.os_terminator import OsTerminator
from ...services.auto_quit.ports import WindowSource
from ...services.auto_quit.service import AutoQuitService
from ...services.auto_quit.source_selection import SOURCE_WAYLAND, SOURCE_X11, choose_window_source
from ...services.keep_awake.scheduler import GLibScheduler
from ..context import AppContext

log = logging.getLogger(__name__)

_ENABLED_KEY = "auto-quit-enabled"


def _started(service: AutoQuitService) -> bool:
    """Subscribe to the window source, reporting whether it took.

    Constructing a source imports nothing: the X11 one pulls the Wnck typelib on
    first subscribe, precisely so that GTK 3 is not loaded into a GTK 4 process
    unless the feature is really used. Guarding only construction therefore
    guards the half that cannot fail, and on a session where that import loses
    the race the whole application goes down instead of the feature.
    """
    try:
        service.start()
    except Exception as error:
        log.warning("auto-quit could not start", extra={"error": str(error)})
        return False
    return True


class AutoQuitFeature:
    """Owns the auto-quit service and the window source behind it."""

    def __init__(self, context: AppContext) -> None:
        self._context = context
        self._service: AutoQuitService | None = None
        source = self._create_window_source()
        if source is None:
            return
        service = AutoQuitService(
            source=source,
            terminator=OsTerminator(),
            scheduler=GLibScheduler(),
            exceptions=lambda: context.config.auto_quit_exceptions,
            system_ids=AUTO_QUIT_SYSTEM_WHITELIST,
            enabled=lambda: context.config.get_bool(_ENABLED_KEY),
        )
        self._service = service if _started(service) else None

    @property
    def is_available(self) -> bool:
        return self._service is not None

    def _create_window_source(self) -> WindowSource | None:
        """Pick the X11 or Wayland-extension window source, or none if neither."""
        kind = choose_window_source(
            has_x11=self._context.has(SESSION_X11),
            has_wayland_source=self._context.has(WAYLAND_WINDOW_SOURCE),
        )
        try:
            if kind == SOURCE_X11:
                from ...services.auto_quit.wnck_source import WnckWindowSource

                return WnckWindowSource()
            if kind == SOURCE_WAYLAND:
                from ...services.auto_quit.shell_extension_source import ShellExtensionWindowSource

                return ShellExtensionWindowSource()
        except Exception as error:
            log.warning("auto-quit window source unavailable", extra={"error": str(error)})
            return None
        return None
