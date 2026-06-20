"""A compact history sparkline drawn with Cairo.

A :class:`Gtk.DrawingArea` that plots a normalised polyline of recent metric
values. It autoscales to the visible window's min/max and follows the current
theme foreground colour, so it reads on both light and dark themes.
"""

from __future__ import annotations

from collections.abc import Sequence

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

_DEFAULT_WIDTH = 72
_DEFAULT_HEIGHT = 22
_LINE_WIDTH = 1.5
_VERTICAL_PADDING = 2.0
_MIN_POINTS = 2


class Sparkline(Gtk.DrawingArea):
    """Plots a small, autoscaled line chart of recent values."""

    def __init__(self, width: int = _DEFAULT_WIDTH, height: int = _DEFAULT_HEIGHT) -> None:
        super().__init__()
        self.set_content_width(width)
        self.set_content_height(height)
        self.set_valign(Gtk.Align.CENTER)
        self._values: tuple[float, ...] = ()
        self.set_draw_func(self._draw)

    def set_values(self, values: Sequence[float]) -> None:
        """Replace the plotted series and request a redraw."""
        self._values = tuple(values)
        self.queue_draw()

    def _draw(self, _area: Gtk.DrawingArea, cr: object, width: int, height: int) -> None:
        values = self._values
        if len(values) < _MIN_POINTS:
            return
        low = min(values)
        span = max(values) - low or 1.0
        usable_height = height - 2 * _VERTICAL_PADDING
        step = width / (len(values) - 1)

        color = self.get_color()
        cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)  # type: ignore[attr-defined]
        cr.set_line_width(_LINE_WIDTH)  # type: ignore[attr-defined]
        for index, value in enumerate(values):
            x = index * step
            y = height - _VERTICAL_PADDING - (value - low) / span * usable_height
            if index == 0:
                cr.move_to(x, y)  # type: ignore[attr-defined]
            else:
                cr.line_to(x, y)  # type: ignore[attr-defined]
        cr.stroke()  # type: ignore[attr-defined]
