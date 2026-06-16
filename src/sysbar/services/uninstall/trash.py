"""Trash adapter using ``Gio.File.trash`` (reversible, never ``rm``)."""

from __future__ import annotations

import logging

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

log = logging.getLogger(__name__)


class GioTrash:
    """Move a path to the desktop trash."""

    def trash(self, path: str) -> bool:
        try:
            return bool(Gio.File.new_for_path(path).trash(None))
        except GLib.Error as error:
            log.warning("could not trash path", extra={"path": path, "error": str(error)})
            return False
