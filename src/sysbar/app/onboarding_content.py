"""What the welcome window says about this computer, in words a user would use.

The capability detectors answer technical questions ("is there an X11
session?", "is polkit reachable?"). A new user asks a different one: what can
Sysbar do here, and what do I do about the rest. This module maps one onto the
other. Pure: it reads a capability snapshot and returns text.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from ..core.capabilities import (
    APPINDICATOR,
    GLOBAL_SHORTCUTS,
    GNOME_DESKTOP,
    LOGIND,
    PIPEWIRE_PULSE,
    POLKIT,
    SENSORS,
    SESSION_X11,
    UPOWER,
    WAYLAND_WINDOW_SOURCE,
)
from ..core.config import Config
from ..core.constants import PLACEMENT_BAR, PLACEMENT_OFF
from ..core.i18n import _

# The two values the welcome window offers to show in the bar from day one.
STARTER_METRICS = ("cpu", "memory")

TOP_BAR_ICON = "Top-bar icon"
AUTO_QUIT = "Close apps automatically"

State = Mapping[str, bool]


@dataclass(frozen=True)
class MissingFeature:
    """A feature this computer cannot run, with what would make it work."""

    title: str
    hint: str


@dataclass(frozen=True)
class CapabilityReport:
    """Features ready to use, and the ones that are not."""

    ready: tuple[str, ...]
    missing: tuple[MissingFeature, ...]


def _has(name: str) -> Callable[[State], bool]:
    return lambda state: state.get(name, False)


def _auto_quit_available(state: State) -> bool:
    return state.get(SESSION_X11, False) or state.get(WAYLAND_WINDOW_SOURCE, False)


# Feature title, availability test, and the hint shown when it is unavailable.
_FEATURES: tuple[tuple[str, Callable[[State], bool], str], ...] = (
    (
        TOP_BAR_ICON,
        _has(APPINDICATOR),
        "Turn on the “AppIndicator and KStatusNotifierItem Support” extension "
        "in the Extensions app, then log in again.",
    ),
    (
        AUTO_QUIT,
        _auto_quit_available,
        "On Wayland it needs the Sysbar extension for GNOME Shell: run "
        "gnome-extensions enable sysbar-window-manager@andreabonn.github.io "
        "and log in again.",
    ),
    ("Global shortcuts", _has(GLOBAL_SHORTCUTS), "Your desktop does not offer them to apps."),
    ("Temperatures", _has(SENSORS), "No temperature sensors were found on this computer."),
    ("Audio mixer and microphone", _has(PIPEWIRE_PULSE), "Needs PipeWire or PulseAudio."),
    ("Do Not Disturb and dark style", _has(GNOME_DESKTOP), "Needs a GNOME session."),
    ("Keep awake", _has(LOGIND), "Needs systemd-logind."),
    ("Battery", _has(UPOWER), "UPower is not running, so battery levels are unknown."),
    (
        "Remove system packages",
        _has(POLKIT),
        "Needs administrator rights (polkit). Cleaning leftover files still works.",
    ),
)


def describe_capabilities(state: State) -> CapabilityReport:
    """Split the user-facing features into ready and missing, translated.

    A capability absent from ``state`` counts as missing: claiming a feature
    works when nothing was detected is the worse of the two mistakes.
    """
    ready: list[str] = []
    missing: list[MissingFeature] = []
    for title, available, hint in _FEATURES:
        if available(state):
            ready.append(_(title))
        else:
            missing.append(MissingFeature(title=_(title), hint=_(hint)))
    return CapabilityReport(ready=tuple(ready), missing=tuple(missing))


def tray_icon_blocked(state: State) -> bool:
    """Whether no host will show the tray icon, leaving Sysbar invisible."""
    return not state.get(APPINDICATOR, False)


def top_bar_metrics_shown(config: Config) -> bool:
    """Whether every starter metric currently sits in the bar."""
    return all(config.metric_placement(metric) == PLACEMENT_BAR for metric in STARTER_METRICS)


def set_top_bar_metrics(config: Config, *, shown: bool) -> None:
    """Put the starter metrics in the bar, or hide them; other metrics are untouched."""
    placement = PLACEMENT_BAR if shown else PLACEMENT_OFF
    for metric in STARTER_METRICS:
        config.settings.set_string(f"menu-bar-{metric}-placement", placement)
