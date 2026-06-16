"""Interfaces for uninstaller side effects (trash, privileged removal)."""

from __future__ import annotations

from typing import Protocol

from .models import PackageManager


class Trash(Protocol):
    """Moves a path to the desktop trash (reversible)."""

    def trash(self, path: str) -> bool: ...


class PackageRemover(Protocol):
    """Removes a system package via a privileged helper."""

    def remove(self, manager: PackageManager, package_ref: str) -> bool: ...
