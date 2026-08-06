"""Pure derivations from configuration and the latest sample to tray state.

These were methods on the application, so they were excluded from coverage along
with the rest of the GI glue even though none of them touches GTK: they read the
typed config wrapper and the latest :class:`SystemSnapshot` and return a value.
Taking their inputs as arguments instead of reaching through ``self`` makes them
testable, which is the point of the split.

Anything that needs a live service (the quick toggles, the keep-awake manager)
stays with the feature module that owns it; only value-to-value functions live
here.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..core.config import Config
from ..core.constants import (
    GRAPH_METRICS,
    HARDWARE_OPTIONAL_METRICS,
    PLACEMENT_MENU,
    PLACEMENT_OFF,
    TRAY_METRICS,
)
from ..services.metrics import metric_format as mf
from ..services.scenes.models import Scene, scene_display_name
from ..services.system_monitor.snapshot import SystemSnapshot
from .tray.menu_builder import SceneMenuEntry
from .tray_renderer import (
    TrayOptions,
    available_metrics,
    menu_metric_values,
    render_device_rows,
)

# Prefix shown in the tray label while keep awake holds the session.
KEEP_AWAKE_PLAY = "▶"


def tray_options(config: Config) -> TrayOptions:
    """Rendering options for the tray label and menu, read from settings."""
    placements = {metric: config.metric_placement(metric) for metric in TRAY_METRICS}
    return TrayOptions(
        memory_style=config.memory_style,
        temperature_unit=config.temperature_unit,
        **placements,
    )


def graph_metrics(config: Config) -> frozenset[str]:
    """Metrics whose sparkline is enabled in settings (``monitor-graph-*``)."""
    return frozenset(
        metric for metric in GRAPH_METRICS if config.get_bool(f"monitor-graph-{metric}")
    )


def has_menu_metrics(config: Config) -> bool:
    """Whether any metric is placed in the dropdown rather than the bar."""
    return any(config.metric_placement(metric) == PLACEMENT_MENU for metric in TRAY_METRICS)


def wants_tray_sampling(config: Config) -> bool:
    """Whether anything on the tray needs samples at all.

    With every metric hidden and peripheral batteries off, the monitor can stop
    sampling for the tray entirely.
    """
    placed = any(config.metric_placement(metric) != PLACEMENT_OFF for metric in TRAY_METRICS)
    return placed or config.show_device_batteries


def menu_metrics(snapshot: SystemSnapshot | None, options: TrayOptions) -> dict[str, str]:
    """Formatted lines for the metrics placed in the dropdown."""
    if snapshot is None:
        return {}
    return menu_metric_values(snapshot, options)


def menu_device_rows(config: Config, snapshot: SystemSnapshot | None) -> tuple[str, ...]:
    """Peripheral battery lines for the menu, empty when the toggle is off."""
    if not config.show_device_batteries or snapshot is None:
        return ()
    return tuple(render_device_rows(snapshot))


def unavailable_metrics(snapshot: SystemSnapshot | None) -> frozenset[str]:
    """Hardware-optional metrics with no data in the latest snapshot.

    Fail-open: with no snapshot yet nothing is reported unavailable, so the
    Settings rows stay enabled rather than being disabled by mistake.
    """
    if snapshot is None:
        return frozenset()
    present = available_metrics(snapshot, TrayOptions())
    return frozenset(metric for metric in HARDWARE_OPTIONAL_METRICS if metric not in present)


def countdown_text(*, active: bool, show: bool, remaining_seconds: float | None) -> str:
    """The keep-awake segment of the tray label.

    Empty when the session is off or the countdown is disabled; the bare play
    marker for an indefinite session; marker plus time for a timed one.
    """
    if not active or not show:
        return ""
    if remaining_seconds is None:
        return KEEP_AWAKE_PLAY
    return f"{KEEP_AWAKE_PLAY} {mf.format_countdown(remaining_seconds)}"


def scene_entries(scenes: Iterable[Scene], active_id: str) -> tuple[SceneMenuEntry, ...]:
    """Tray submenu rows for the known scenes, flagging the active one.

    The name is resolved to its display form here, so that everything downstream
    can treat it as final text. Only the built-in scenes are translated: see
    :data:`sysbar.services.scenes.models.PRESET_SCENE_IDS`.
    """
    return tuple(
        SceneMenuEntry(id=scene.id, name=scene_display_name(scene), active=scene.id == active_id)
        for scene in scenes
    )
