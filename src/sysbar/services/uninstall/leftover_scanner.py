"""Pure leftover scanner.

Looks for an application's residue in the standard XDG locations under a home
directory. The home directory is a parameter so the scan is unit-tested against
a temporary filesystem.
"""

from __future__ import annotations

from pathlib import Path

from .models import Leftover, LeftoverCategory

_XDG_DIRS = (
    (Path(".config"), LeftoverCategory.CONFIG),
    (Path(".cache"), LeftoverCategory.CACHE),
    (Path(".local") / "share", LeftoverCategory.DATA),
    (Path(".local") / "state", LeftoverCategory.STATE),
)


def directory_size(path: Path) -> int:
    """Total size in bytes of a file or directory tree."""
    if path.is_file():
        return path.stat().st_size
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())


def _candidate_names(app_name: str, app_id: str | None) -> list[str]:
    names = [app_name, app_name.lower()]
    if app_id:
        names.append(app_id)
    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        if name and name not in seen:
            seen.add(name)
            result.append(name)
    return result


def scan_leftovers(app_name: str, app_id: str | None, home: Path) -> list[Leftover]:
    """Return residue directories/files found for the application."""
    leftovers: list[Leftover] = []
    seen_paths: set[Path] = set()
    names = _candidate_names(app_name, app_id)

    for base, category in _XDG_DIRS:
        for name in names:
            candidate = home / base / name
            if candidate.exists() and candidate not in seen_paths:
                seen_paths.add(candidate)
                leftovers.append(
                    Leftover(
                        category=category, path=str(candidate), size_bytes=directory_size(candidate)
                    )
                )

    if app_id:
        flatpak_dir = home / ".var" / "app" / app_id
        if flatpak_dir.exists():
            leftovers.append(
                Leftover(
                    category=LeftoverCategory.FLATPAK_DATA,
                    path=str(flatpak_dir),
                    size_bytes=directory_size(flatpak_dir),
                )
            )

    leftovers.extend(_desktop_entries(app_id, home, seen_paths))
    return leftovers


def _desktop_entries(app_id: str | None, home: Path, seen: set[Path]) -> list[Leftover]:
    if not app_id:
        return []
    entry = home / ".local" / "share" / "applications" / f"{app_id}.desktop"
    if not entry.is_file() or entry in seen:
        return []
    return [
        Leftover(
            category=LeftoverCategory.DESKTOP_ENTRY,
            path=str(entry),
            size_bytes=entry.stat().st_size,
        )
    ]
