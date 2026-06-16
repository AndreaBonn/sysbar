"""Desktop notifications via ``Gio.Notification``.

Used for keep-awake session end and battery protection. Never carries sensitive
data. Boundary code (delegates to the application's notification channel).
"""

from __future__ import annotations

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio  # noqa: E402


class Notifier:
    """Sends desktop notifications through the application."""

    def __init__(self, application: Gio.Application) -> None:
        self._application = application

    def notify(self, title: str, body: str, notification_id: str = "sysbar") -> None:
        notification = Gio.Notification.new(title)
        notification.set_body(body)
        self._application.send_notification(notification_id, notification)
