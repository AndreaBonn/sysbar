"""libwnck window source (X11 only).

Subscribes to ``Wnck.Screen`` open/close signals and reports each window's id,
WM_CLASS-derived app id and PID. Boundary code; the tracking logic is tested
separately. Requires an X11 session.
"""

from __future__ import annotations

import logging
from typing import Any

from .ports import WindowClosedCallback, WindowOpenedCallback

log = logging.getLogger(__name__)


class WnckWindowSource:
    """Emits window events from the default ``Wnck.Screen``."""

    def __init__(self) -> None:
        self._on_opened: WindowOpenedCallback | None = None
        self._on_closed: WindowClosedCallback | None = None

    def subscribe(  # pragma: no cover - Wnck.Screen.get_default boundary (requires X11)
        self, on_opened: WindowOpenedCallback, on_closed: WindowClosedCallback
    ) -> None:
        import gi

        # Imported here, not at module level: the Wnck-3.0 typelib pulls in GTK 3,
        # and gi allows a single GTK version per process. A module-level import
        # would lock the process to GTK 3 and break the GTK4 UI at import time.
        gi.require_version("Wnck", "3.0")
        from gi.repository import Wnck

        self._on_opened = on_opened
        self._on_closed = on_closed
        screen = Wnck.Screen.get_default()
        screen.force_update()
        screen.connect("window-opened", self._handle_opened)
        screen.connect("window-closed", self._handle_closed)
        for window in screen.get_windows():
            self._handle_opened(screen, window)

    def _handle_opened(self, _screen: Any, window: Any) -> None:
        if self._on_opened is not None:
            self._on_opened(window.get_xid(), self._app_id(window), self._pid(window))

    def _handle_closed(self, _screen: Any, window: Any) -> None:
        if self._on_closed is not None:
            self._on_closed(window.get_xid())

    @staticmethod
    def _app_id(window: Any) -> str | None:
        return window.get_class_group_name() or None

    @staticmethod
    def _pid(window: Any) -> int | None:
        pid = window.get_pid()
        return pid if pid else None
