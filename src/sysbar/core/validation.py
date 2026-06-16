"""Pure validation/sanitization helpers for configuration values.

These functions mirror the ``Defaults.sanitized*`` helpers of the macOS
original. They are deliberately free of GI/GSettings imports so the core
configuration rules can be unit-tested in isolation.
"""

from __future__ import annotations

from .constants import (
    ALLOWED_BATTERY_LIMITS,
    ALLOWED_DURATIONS,
    ALLOWED_INTERVALS,
    ALLOWED_MEMORY_STYLES,
    ALLOWED_TEMPERATURE_UNITS,
    DEFAULT_BATTERY_LIMIT_PERCENT,
    DEFAULT_DURATION_MINUTES,
    DEFAULT_MEMORY_STYLE,
    DEFAULT_MONITOR_INTERVAL_SECONDS,
    DEFAULT_TEMPERATURE_UNIT,
    MAX_APP_VOLUME,
    MIN_APP_VOLUME,
)


def sanitized_duration(value: int) -> int:
    """Return ``value`` if it is an allowed keep-awake duration, else the default."""
    return value if value in ALLOWED_DURATIONS else DEFAULT_DURATION_MINUTES


def sanitized_battery_limit(value: int) -> int:
    """Return ``value`` if it is an allowed battery cut-off, else the default."""
    return value if value in ALLOWED_BATTERY_LIMITS else DEFAULT_BATTERY_LIMIT_PERCENT


def sanitized_monitor_interval(value: int) -> int:
    """Return ``value`` if it is an allowed sampling interval, else the default."""
    return value if value in ALLOWED_INTERVALS else DEFAULT_MONITOR_INTERVAL_SECONDS


def sanitized_memory_style(value: str) -> str:
    """Return ``value`` if it is a known memory style, else the default."""
    return value if value in ALLOWED_MEMORY_STYLES else DEFAULT_MEMORY_STYLE


def sanitized_temperature_unit(value: str) -> str:
    """Return ``value`` if it is a known temperature unit, else the default."""
    return value if value in ALLOWED_TEMPERATURE_UNITS else DEFAULT_TEMPERATURE_UNIT


def sanitized_app_volume(value: float) -> float:
    """Clamp a per-application volume into the [0.0, 2.0] range."""
    return min(max(value, MIN_APP_VOLUME), MAX_APP_VOLUME)


def sanitized_app_id_list(values: list[str]) -> list[str]:
    """Trim, drop empties and de-duplicate (order-preserving) a list of app ids."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        app_id = raw.strip()
        if not app_id or app_id in seen:
            continue
        seen.add(app_id)
        result.append(app_id)
    return result
