"""Application icon registration.

GTK4 has no per-window icon API: a window's icon is resolved from the application
id against the icon theme. An installed Sysbar ships the branded icon under
``/usr/share/icons/hicolor`` (a system theme path resolved automatically); a
source checkout only has it under ``<repo>/data/icons``. Registering that
directory on the default icon theme lets in-app ``Gtk.Image(icon_name=...)``
resolve the logo in both cases, so the panel and settings show the brand instead
of GNOME's generic fallback.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gi.repository import Gdk

log = logging.getLogger(__name__)

# data/icons relative to this file: core/ -> sysbar/ -> src/ -> <repo>.
_SOURCE_ICONS_DIR = Path(__file__).resolve().parents[3] / "data" / "icons"


def app_icons_dir() -> Path | None:
    """Return the source-checkout hicolor icon root, or ``None`` when absent.

    Returns
    -------
    Path | None
        The ``data/icons`` directory in a source checkout, or ``None`` in an
        installed build where the icons live under the system theme path and no
        extra search path is needed.
    """
    return _SOURCE_ICONS_DIR if _SOURCE_ICONS_DIR.is_dir() else None


def register_app_icons(display: Gdk.Display | None) -> bool:
    """Register the source icon directory on *display*'s icon theme.

    Parameters
    ----------
    display : Gdk.Display | None
        The display whose icon theme gains the search path. ``None`` is tolerated
        (no display yet) and is a no-op.

    Returns
    -------
    bool
        ``True`` when a search path was added (source checkout), ``False`` when
        there is nothing to add (installed build or no display). Idempotent: GTK
        ignores a path already registered.
    """
    icons_dir = app_icons_dir()
    if display is None or icons_dir is None:
        return False

    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    Gtk.IconTheme.get_for_display(display).add_search_path(str(icons_dir))
    log.debug("registered app icon search path", extra={"path": str(icons_dir)})
    return True


def has_app_icon(display: Gdk.Display | None) -> bool:
    """Return whether the branded icon resolves in *display*'s icon theme.

    Lets callers fall back to a plain title when the icon has not been generated
    yet, instead of rendering GTK's "broken image" placeholder.

    Parameters
    ----------
    display : Gdk.Display | None
        The display whose icon theme is queried. ``None`` yields ``False``.

    Returns
    -------
    bool
        ``True`` when ``APP_ICON_NAME`` is known to the theme.
    """
    if display is None:
        return False

    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    from .constants import APP_ICON_NAME

    return bool(Gtk.IconTheme.get_for_display(display).has_icon(APP_ICON_NAME))
