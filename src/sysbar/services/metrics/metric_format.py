"""Pure metric formatting (port of the macOS ``MetricFormat``).

All functions are side-effect free and unit-tested with concrete values.
"""

from __future__ import annotations

from ...core.constants import TEMPERATURE_FAHRENHEIT

_BYTE_STEP = 1024.0
_BYTE_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert a Celsius temperature to Fahrenheit."""
    return celsius * 9.0 / 5.0 + 32.0


def format_temperature(celsius: float, unit: str) -> str:
    """Format a Celsius reading in the requested unit, rounded to a degree."""
    if unit == TEMPERATURE_FAHRENHEIT:
        return f"{round(celsius_to_fahrenheit(celsius))}°F"
    return f"{round(celsius)}°C"


def format_bytes(num_bytes: float) -> str:
    """Format a byte count with a binary-scaled unit (e.g. ``1.2 MB``)."""
    value = float(num_bytes)
    for unit in _BYTE_UNITS:
        if abs(value) < _BYTE_STEP or unit == _BYTE_UNITS[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= _BYTE_STEP
    return f"{value:.1f} {_BYTE_UNITS[-1]}"


def format_rate(bytes_per_second: float) -> str:
    """Format a transfer rate (e.g. ``2.1 MB/s``)."""
    return f"{format_bytes(bytes_per_second)}/s"


def format_percent(value: float) -> str:
    """Format a 0..100 percentage rounded to an integer (e.g. ``23%``)."""
    return f"{round(value)}%"


def format_countdown(seconds: float) -> str:
    """Format remaining time as ``M:SS`` (or ``H:MM:SS`` past an hour)."""
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_uptime(seconds: float) -> str:
    """Format an uptime in seconds as a compact ``2d 3h 15m`` string."""
    total_minutes = int(seconds) // 60
    days, remainder = divmod(total_minutes, 60 * 24)
    hours, minutes = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)
