"""Shared window footer: a copyright credit linking to the author's GitHub.

Used as the bottom bar of every Sysbar window. The credit is a :class:`Gtk.LinkButton`,
so activation opens the URI through the desktop default handler with no extra wiring.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from ..core.constants import AUTHOR_GITHUB_URL, AUTHOR_NAME  # noqa: E402

_FOOTER_LABEL = f"© {AUTHOR_NAME}"


def build_footer() -> Gtk.Widget:
    """Return a centered copyright link suitable for a window's bottom bar."""
    link = Gtk.LinkButton(uri=AUTHOR_GITHUB_URL, label=_FOOTER_LABEL)
    link.add_css_class("flat")
    link.set_halign(Gtk.Align.CENTER)
    link.set_margin_top(4)
    link.set_margin_bottom(4)
    return link
