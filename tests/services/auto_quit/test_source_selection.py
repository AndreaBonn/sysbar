from sysbar.services.auto_quit.source_selection import (
    SOURCE_NONE,
    SOURCE_WAYLAND,
    SOURCE_X11,
    choose_window_source,
)


def test_prefers_x11_when_available() -> None:
    assert choose_window_source(has_x11=True, has_wayland_source=True) == SOURCE_X11


def test_uses_wayland_extension_when_no_x11() -> None:
    assert choose_window_source(has_x11=False, has_wayland_source=True) == SOURCE_WAYLAND


def test_none_when_neither_available() -> None:
    assert choose_window_source(has_x11=False, has_wayland_source=False) == SOURCE_NONE
