"""What the top of the panel says, before the user reads a single number.

The panel lists raw values; whether 61% memory is a problem depends on knowing
the machine. :func:`summarize` answers that question in one line, and
:func:`quick_tiles` decides which quick toggles the panel offers and how each
one reads right now. Pure: values in, display data out.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.constants import (
    DEFAULT_TEMPERATURE_UNIT,
    SUMMARY_BATTERY_LOW_PERCENT,
    SUMMARY_CPU_BUSY_PERCENT,
    SUMMARY_HOT_CELSIUS,
    SUMMARY_MEMORY_FULL_PERCENT,
)
from ..core.i18n import _
from ..services.metrics import metric_format as mf
from ..services.system_monitor.processes import ProcessUsage
from ..services.system_monitor.snapshot import SystemSnapshot
from .tray.menu_builder import QuickToggleState

# memory_pressure_level values worth naming; "normal" is left unsaid.
_PRESSURED = frozenset({"warning", "critical"})
_PRESSURE_LABELS = {"warning": "high pressure", "critical": "critical pressure"}

TILE_KEEP_AWAKE = "keep-awake"
TILE_MICROPHONE = "microphone"
TILE_DND = "dnd"
TILE_DARK = "dark"


@dataclass(frozen=True)
class PanelSummary:
    """One line on the state of the machine, plus a supporting detail."""

    ok: bool
    title: str
    detail: str


@dataclass(frozen=True)
class QuickTile:
    """A quick toggle as the panel shows it."""

    id: str
    label: str
    icon_name: str
    active: bool


def summarize(
    snapshot: SystemSnapshot,
    busiest: ProcessUsage | None,
    *,
    temperature_unit: str = DEFAULT_TEMPERATURE_UNIT,
) -> PanelSummary:
    """Name the first problem worth a look, or say that all is normal."""
    problem = _first_problem(snapshot, temperature_unit)
    detail = (
        _("Busiest app: {name}, {cpu} CPU").format(
            name=busiest.name, cpu=mf.format_percent(busiest.cpu_percent)
        )
        if busiest is not None and busiest.name
        else ""
    )
    if problem is None:
        return PanelSummary(ok=True, title=_("All normal"), detail=detail)
    return PanelSummary(ok=False, title=problem, detail=detail)


def _first_problem(snapshot: SystemSnapshot, temperature_unit: str) -> str | None:
    cpu, memory = snapshot.cpu_percent, snapshot.memory_percent
    if cpu is not None and cpu >= SUMMARY_CPU_BUSY_PERCENT:
        return _("CPU busy: {value}").format(value=mf.format_percent(cpu))
    if memory is not None and memory >= SUMMARY_MEMORY_FULL_PERCENT:
        return _("Memory almost full: {value}").format(value=mf.format_percent(memory))
    if snapshot.memory_pressure in _PRESSURED:
        return _("Memory under pressure")
    temp = snapshot.cpu_temp_celsius
    if temp is not None and temp >= SUMMARY_HOT_CELSIUS:
        return _("Running hot: {value}").format(value=mf.format_temperature(temp, temperature_unit))
    battery = snapshot.battery_percent
    if battery is not None and snapshot.on_battery and battery <= SUMMARY_BATTERY_LOW_PERCENT:
        return _("Battery low: {value}").format(value=mf.format_percent(battery))
    return None


def quick_tiles(toggles: QuickToggleState, *, keep_awake_on: bool) -> tuple[QuickTile, ...]:
    """Keep awake always; the system toggles only where this session supports them."""
    tiles = [QuickTile(TILE_KEEP_AWAKE, _("Keep awake"), "weather-clear-symbolic", keep_awake_on)]
    if toggles.mic_available:
        icon = (
            "microphone-disabled-symbolic"
            if toggles.mic_muted
            else "audio-input-microphone-symbolic"
        )
        tiles.append(QuickTile(TILE_MICROPHONE, _("Microphone"), icon, not toggles.mic_muted))
    if toggles.dnd_available:
        tiles.append(
            QuickTile(
                TILE_DND, _("Do Not Disturb"), "notifications-disabled-symbolic", toggles.dnd_active
            )
        )
    if toggles.dark_available:
        tiles.append(
            QuickTile(
                TILE_DARK, _("Dark style"), "weather-clear-night-symbolic", toggles.dark_active
            )
        )
    return tuple(tiles)


def memory_text(snapshot: SystemSnapshot) -> str | None:
    """Memory use, with the pressure named only when it is not normal."""
    if snapshot.memory_percent is None:
        return None
    percent = mf.format_percent(snapshot.memory_percent)
    pressure = _PRESSURE_LABELS.get(snapshot.memory_pressure or "")
    return f"{percent} · {_(pressure)}" if pressure else percent


def battery_text(snapshot: SystemSnapshot) -> str | None:
    """Battery level, and whether it is charging or draining."""
    if snapshot.battery_percent is None:
        return None
    percent = mf.format_percent(snapshot.battery_percent)
    if snapshot.battery_charging:
        return f"{percent} · {_('charging')}"
    if snapshot.on_battery:
        return f"{percent} · {_('on battery')}"
    return percent
