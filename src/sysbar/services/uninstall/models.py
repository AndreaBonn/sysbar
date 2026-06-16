"""Uninstaller models: package manager, leftover categories and phases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PackageManager(StrEnum):
    """How an application was installed."""

    APT = "apt"
    SNAP = "snap"
    FLATPAK = "flatpak"
    MANUAL = "manual"


class LeftoverCategory(StrEnum):
    """The kind of user-level residue an uninstall leaves behind."""

    CONFIG = "config"
    CACHE = "cache"
    DATA = "data"
    STATE = "state"
    DESKTOP_ENTRY = "desktop_entry"
    FLATPAK_DATA = "flatpak_data"


class Phase(StrEnum):
    """The uninstaller workflow phase."""

    EMPTY = "empty"
    SCANNING = "scanning"
    RESULTS = "results"
    REMOVING = "removing"
    DONE = "done"


@dataclass(frozen=True)
class AppTarget:
    """An application selected for removal."""

    name: str
    app_id: str | None
    exec_path: str | None
    manager: PackageManager
    package_ref: str | None = None


@dataclass(frozen=True)
class Leftover:
    """One user-level residue, with its size on disk."""

    category: LeftoverCategory
    path: str
    size_bytes: int


@dataclass(frozen=True)
class RemovalResult:
    """Outcome of a removal: bytes freed and the references that failed."""

    freed_bytes: int
    failed: list[str]


def recoverable_bytes(leftovers: list[Leftover]) -> int:
    """Total size of the given leftovers."""
    return sum(leftover.size_bytes for leftover in leftovers)
