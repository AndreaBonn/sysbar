"""Wording and defaults for the Preferences window that a test can check.

The window itself is GTK glue; what it says about a placement, an alert or the
top bar is decided here, so it can be read and asserted without a display.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.i18n import _

# Where a tray metric goes. The internal names ("bar", "menu") stay in GSettings;
# the user sees a place.
PLACEMENT_OPTIONS: tuple[tuple[str, str], ...] = (
    ("off", "Hidden"),
    ("bar", "Top bar"),
    ("menu", "Menu only"),
)


@dataclass(frozen=True)
class AlertSpec:
    """One threshold alert as Preferences presents it."""

    key: str
    title: str
    upper: int
    # Value set when the alert is switched on; 0 in GSettings means "off".
    suggested: int
    below: bool = False
    unit: str = "%"
    # Fires only after the value has held for alert-cpu-seconds.
    sustained: bool = False


ALERTS: tuple[AlertSpec, ...] = (
    AlertSpec("alert-cpu-percent", "CPU busy", upper=100, suggested=90, sustained=True),
    AlertSpec("alert-memory-percent", "Memory almost full", upper=100, suggested=90),
    AlertSpec("alert-disk-percent", "Disk almost full", upper=100, suggested=90),
    AlertSpec("alert-temperature-celsius", "Running hot", upper=150, suggested=90, unit="°C"),
    AlertSpec("alert-battery-percent", "Battery low", upper=100, suggested=15, below=True),
)

CPU_SECONDS_KEY = "alert-cpu-seconds"


def alert_subtitle(spec: AlertSpec, value: int, *, cpu_seconds: int) -> str:
    """Say in words when the alert fires, or that it is off."""
    if value <= 0:
        return _("Not active")
    amount = f"{value}{spec.unit}"
    if spec.below:
        return _("Below {amount}").format(amount=amount)
    if spec.sustained:
        return _("Above {amount} for {seconds} seconds").format(amount=amount, seconds=cpu_seconds)
    return _("Above {amount}").format(amount=amount)


def tray_preview_text(label: str | None) -> str:
    """The live top-bar preview; an empty bar is named rather than left blank.

    ``None`` means no sample has arrived yet, which is not the same as a bar
    with nothing placed in it.
    """
    if label is None:
        return _("Waiting for the first reading…")
    return label or _("Only the icon: nothing is placed in the top bar")
