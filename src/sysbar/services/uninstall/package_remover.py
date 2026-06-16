"""Privileged package removal via pkexec/flatpak.

Boundary code: builds argument lists (never a shell) and authorizes through
polkit. APT/snap removals run under ``pkexec``; flatpak uses its own user-scope
removal.
"""

from __future__ import annotations

import logging
import subprocess

from .models import PackageManager

log = logging.getLogger(__name__)

_REMOVE_TIMEOUT_SECONDS = 120


def _command(manager: PackageManager, package_ref: str) -> list[str] | None:
    if manager is PackageManager.APT:
        return ["pkexec", "apt-get", "purge", "-y", package_ref]
    if manager is PackageManager.SNAP:
        return ["pkexec", "snap", "remove", "--purge", package_ref]
    if manager is PackageManager.FLATPAK:
        return ["flatpak", "uninstall", "--delete-data", "-y", package_ref]
    return None


class PkexecPackageRemover:
    """Remove a system package, authorizing via polkit where needed."""

    def remove(self, manager: PackageManager, package_ref: str) -> bool:
        command = _command(manager, package_ref)
        if command is None:
            return False
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=_REMOVE_TIMEOUT_SECONDS,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as error:
            log.warning("package removal failed", extra={"ref": package_ref, "error": str(error)})
            return False
        if result.returncode != 0:
            log.warning("package removal returned error", extra={"ref": package_ref})
        return result.returncode == 0
