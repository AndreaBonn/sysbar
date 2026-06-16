"""Package query backed by dpkg/snap/flatpak.

Boundary code: runs read-only queries with argument lists (never a shell). The
identification logic that consumes it is unit-tested separately.
"""

from __future__ import annotations

import logging
import subprocess

log = logging.getLogger(__name__)

_SNAP_PREFIX = "/snap/"
_QUERY_TIMEOUT_SECONDS = 5


class CommandPackageQuery:
    """Answer ownership questions via system package tools."""

    def snap_name(self, path: str) -> str | None:
        if not path.startswith(_SNAP_PREFIX):
            return None
        parts = path[len(_SNAP_PREFIX) :].split("/", 1)
        return parts[0] or None

    def owning_apt_package(self, path: str) -> str | None:
        output = self._run(["dpkg", "-S", path])
        if output is None:
            return None
        return output.split(":", 1)[0].split(",", 1)[0].strip() or None

    def flatpak_app_id(self, app_id: str | None) -> str | None:
        if not app_id:
            return None
        output = self._run(["flatpak", "info", app_id])
        return app_id if output is not None else None

    @staticmethod
    def _run(args: list[str]) -> str | None:
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=_QUERY_TIMEOUT_SECONDS,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        return result.stdout if result.returncode == 0 else None
