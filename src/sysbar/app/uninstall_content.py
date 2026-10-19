"""What the uninstaller window says, decided where a test can read it.

The service speaks in categories, package managers and absolute paths. The
window has to say "Menu shortcut", "Installed with apt" and "~/.config/gimp",
and to keep its red button off until there is something to move. Pure.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..core.i18n import _
from ..services.metrics import metric_format as mf
from ..services.palette.matcher import normalize
from ..services.uninstall.models import Leftover, LeftoverCategory, PackageManager, RemovalResult

_CATEGORY_LABELS = {
    LeftoverCategory.CONFIG: "Settings",
    LeftoverCategory.CACHE: "Cache",
    LeftoverCategory.DATA: "Saved data",
    LeftoverCategory.STATE: "History and state",
    LeftoverCategory.DESKTOP_ENTRY: "Menu shortcut",
    LeftoverCategory.FLATPAK_DATA: "Flatpak data",
}


@dataclass(frozen=True)
class RemovalSummary:
    """The status line and the state of the remove button."""

    status: str
    button: str
    can_remove: bool


def category_label(category: LeftoverCategory) -> str:
    return _(_CATEGORY_LABELS[category])


def filter_apps(names: Sequence[str], query: str) -> list[int]:
    """Positions of the names containing ``query``, ignoring case and accents.

    Positions rather than names: two installed apps can share a display name,
    and both must stay selectable.
    """
    needle = normalize(query.strip())
    return [index for index, name in enumerate(names) if needle in normalize(name)]


def short_path(path: str, *, home: str) -> str:
    """Show a path under the home directory as ``~/...``."""
    prefix = home.rstrip("/") + "/"
    return "~/" + path[len(prefix) :] if path.startswith(prefix) else path


def removal_summary(*, chosen: bool, count: int, size_bytes: int) -> RemovalSummary:
    """Keep the destructive button off until an app with leftovers is chosen."""
    idle_button = _("Move to the Trash")
    if not chosen:
        return RemovalSummary(_("Choose an app to see what it left behind"), idle_button, False)
    if count == 0:
        return RemovalSummary(_("Nothing left to clean up for this app"), idle_button, False)
    size = mf.format_bytes(size_bytes)
    return RemovalSummary(
        status=_("Found {count} items, {size} in total").format(count=count, size=size),
        button=_("Move {count} items ({size}) to the Trash").format(count=count, size=size),
        can_remove=True,
    )


def package_subtitle(manager: PackageManager, package_ref: str | None, *, removable: bool) -> str:
    if removable and package_ref:
        return _("Installed with {manager}: {package}").format(
            manager=manager.value, package=package_ref
        )
    return _("Not available: installed by hand, or no administrator rights")


def leftover_subtitle(leftover: Leftover, *, home: str) -> str:
    """Show the residue size and a home-relative path."""
    return f"{mf.format_bytes(leftover.size_bytes)} · {short_path(str(leftover.path), home=home)}"


def removal_message(result: RemovalResult) -> str:
    """Describe the bytes moved to the Trash and any failed items."""
    freed = mf.format_bytes(result.freed_bytes)
    if result.failed:
        return _("Freed {size}; {count} items could not be moved").format(
            size=freed, count=len(result.failed)
        )
    return _("Done: {size} moved to the Trash").format(size=freed)
