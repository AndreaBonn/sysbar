"""Application life cycle.

A single-instance ``Adw.Application`` with no main window: Sysbar lives in the
tray. Services are lazy singletons toggled by their GSettings keys. The tray
itself (StatusNotifierItem/DBusMenu) is wired in milestone 2.
"""

from __future__ import annotations

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio  # noqa: E402

from ..core.capabilities import Capabilities  # noqa: E402
from ..core.config import Config  # noqa: E402
from ..core.constants import APP_ID  # noqa: E402
from ..core.localization import install_language  # noqa: E402

log = logging.getLogger(__name__)


class SysbarApplication(Adw.Application):
    """Top-level application object."""

    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self._config: Config | None = None
        self._capabilities = Capabilities()

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        self._config = Config()
        install_language(self._config.get_string("app-language"))
        self._capabilities.refresh()
        self._install_actions()
        log.info("application started", extra={"capabilities": self._capabilities.snapshot()})

    def do_activate(self) -> None:
        # No window to present yet; hold the application alive in the tray.
        self.hold()

    def _install_actions(self) -> None:
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)

    @property
    def capabilities(self) -> Capabilities:
        return self._capabilities

    @property
    def config(self) -> Config:
        if self._config is None:
            self._config = Config()
        return self._config
