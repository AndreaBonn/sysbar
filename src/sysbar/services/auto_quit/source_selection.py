"""Pick the window source for the current session.

X11 is preferred (libwnck is reliable and needs no extension); on Wayland the
GNOME Shell extension is used when present; otherwise auto-quit has no source and
degrades with an explicit message. Pure and unit-tested.
"""

from __future__ import annotations

SOURCE_X11 = "x11"
SOURCE_WAYLAND = "wayland"
SOURCE_NONE = "none"


def choose_window_source(*, has_x11: bool, has_wayland_source: bool) -> str:
    """Return the window source to use given the detected capabilities."""
    if has_x11:
        return SOURCE_X11
    if has_wayland_source:
        return SOURCE_WAYLAND
    return SOURCE_NONE
