"""Package manager identification.

Decides how an application was installed from the answers of a package query
port. The decision logic is pure; the query (dpkg/snap/flatpak) is the boundary.
"""

from __future__ import annotations

from typing import Protocol

from .models import AppTarget, PackageManager


class PackageQuery(Protocol):
    """Answers ownership questions about a path or app id."""

    def snap_name(self, path: str) -> str | None: ...
    def owning_apt_package(self, path: str) -> str | None: ...
    def flatpak_app_id(self, app_id: str | None) -> str | None: ...


def identify(
    exec_path: str | None, app_id: str | None, query: PackageQuery
) -> tuple[PackageManager, str | None]:
    """Return the package manager and its package reference for an application.

    Snap is checked before APT (snap files are not owned by dpkg), then flatpak;
    anything else is treated as a manual install.
    """
    if exec_path:
        snap = query.snap_name(exec_path)
        if snap:
            return PackageManager.SNAP, snap
        apt = query.owning_apt_package(exec_path)
        if apt:
            return PackageManager.APT, apt
    flatpak = query.flatpak_app_id(app_id)
    if flatpak:
        return PackageManager.FLATPAK, flatpak
    return PackageManager.MANUAL, None


def target_from_app(
    name: str, *, desktop_id: str | None, exec_path: str | None, query: PackageQuery
) -> AppTarget:
    """Build a target without desktop suffixes so package queries use the app id.

    Executable resolution stays at the system boundary; missing executables
    still allow identification through the flatpak app id.
    """
    app_id = desktop_id or ""
    if app_id.endswith(".desktop"):
        app_id = app_id.removesuffix(".desktop")
    manager, ref = identify(exec_path=exec_path, app_id=app_id or None, query=query)
    return AppTarget(
        name=name,
        app_id=app_id or None,
        exec_path=exec_path,
        manager=manager,
        package_ref=ref,
    )
