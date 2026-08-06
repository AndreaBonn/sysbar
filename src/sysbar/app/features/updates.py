"""Optional release check against the project's GitHub releases.

The request runs on a worker thread so a slow or unreachable network never
delays startup, and the notification is handed back to the main loop, because
GTK objects must not be touched from the worker.
"""

from __future__ import annotations

import threading

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib  # noqa: E402

from ...core.i18n import _  # noqa: E402
from ...services.update_service import UpdateInfo, UpdateService  # noqa: E402
from ..context import AppContext  # noqa: E402

_ENABLED_KEY = "auto-check-updates"
_UPGRADE_HINT = "sudo apt update && sudo apt upgrade sysbar"


class UpdateCheckFeature:
    """Checks for a newer release once at startup, if the user opted in."""

    def __init__(self, context: AppContext) -> None:
        self._context = context

    def start(self) -> None:
        if not self._context.config.get_bool(_ENABLED_KEY):
            return
        threading.Thread(target=self._check, daemon=True).start()

    def _check(self) -> None:
        info = UpdateService().check()
        if info is not None:
            GLib.idle_add(self._announce, info)

    def _announce(self, info: UpdateInfo) -> bool:
        self._context.notifier.notify(
            _("Sysbar update available"),
            f"{info.version} is available. Run: {_UPGRADE_HINT}",
            notification_id="update",
        )
        return False
