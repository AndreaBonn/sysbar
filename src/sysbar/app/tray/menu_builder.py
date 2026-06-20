"""Build the tray dropdown as a fixed-shape :class:`MenuItem` tree.

The com.canonical.dbusmenu host (GNOME AppIndicator, KDE) caches item state by
id, so a menu whose node count changes between updates desynchronises: stale
``enabled``/``label`` values bleed onto items that inherited a recycled id,
producing greyed-out or duplicated entries.

To keep ids stable, the tree always has the same nodes in the same order. State
differences live only in the ``visible`` / ``label`` / ``toggle_state``
properties, never in the presence or absence of a node. Hidden items are emitted
with ``visible=False`` rather than dropped.

The module is pure (no GI imports) and unit-tested.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ...core.constants import AUTHOR_NAME, TRAY_METRICS
from ...core.i18n import _
from .menu_model import TOGGLE_OFF, TOGGLE_ON, TYPE_SEPARATOR, MenuItem


@dataclass(frozen=True)
class MenuActions:
    """Activation callbacks for the fixed action rows of the tray menu."""

    toggle_keep_awake: Callable[[], None]
    toggle_microphone: Callable[[], None]
    toggle_dnd: Callable[[], None]
    toggle_dark_mode: Callable[[], None]
    open_panel: Callable[[], None]
    open_shelf: Callable[[], None]
    open_uninstaller: Callable[[], None]
    open_settings: Callable[[], None]
    open_github: Callable[[], None]
    quit: Callable[[], None]


@dataclass(frozen=True)
class QuickToggleState:
    """Availability and on/off state of the quick system toggles."""

    mic_available: bool = False
    mic_muted: bool = False
    mic_in_use: bool = False
    dnd_available: bool = False
    dnd_active: bool = False
    dark_available: bool = False
    dark_active: bool = False


def build_menu_items(
    metric_values: dict[str, str],
    *,
    keep_awake_on: bool,
    shelf_enabled: bool,
    toggles: QuickToggleState,
    actions: MenuActions,
) -> list[MenuItem]:
    """Return the full, fixed menu tree with per-item visibility applied.

    Parameters
    ----------
    metric_values
        Map of metric id to its formatted line, for metrics placed in the menu
        that currently have data. Metrics absent from the map render as a hidden
        slot, preserving the node (and its id) for the next update.
    keep_awake_on
        Whether the keep-awake toggle is currently active.
    shelf_enabled
        Whether the optional "Open shelf" row should be visible.
    actions
        Callbacks wired to the action rows.
    """
    items = _metric_slots(metric_values)
    items.append(MenuItem(item_type=TYPE_SEPARATOR, visible=bool(metric_values)))
    items.extend(
        _action_rows(
            keep_awake_on=keep_awake_on,
            shelf_enabled=shelf_enabled,
            toggles=toggles,
            actions=actions,
        )
    )
    return items


def _metric_slots(metric_values: dict[str, str]) -> list[MenuItem]:
    return [
        MenuItem(
            label=metric_values.get(metric, ""),
            enabled=False,
            visible=metric in metric_values,
        )
        for metric in TRAY_METRICS
    ]


def _action_rows(
    *, keep_awake_on: bool, shelf_enabled: bool, toggles: QuickToggleState, actions: MenuActions
) -> list[MenuItem]:
    return [
        MenuItem(
            label=_("Keep awake"),
            toggle_type="checkmark",
            toggle_state=TOGGLE_ON if keep_awake_on else TOGGLE_OFF,
            action=actions.toggle_keep_awake,
        ),
        *_quick_toggle_rows(toggles=toggles, actions=actions),
        MenuItem(item_type=TYPE_SEPARATOR),
        MenuItem(label=_("Open panel"), action=actions.open_panel),
        MenuItem(label=_("Open shelf"), action=actions.open_shelf, visible=shelf_enabled),
        MenuItem(label=_("Uninstall app…"), action=actions.open_uninstaller),
        MenuItem(label=_("Settings"), action=actions.open_settings),
        MenuItem(item_type=TYPE_SEPARATOR),
        MenuItem(label=_("Quit"), action=actions.quit),
        MenuItem(item_type=TYPE_SEPARATOR),
        MenuItem(label=f"© {AUTHOR_NAME}", action=actions.open_github),
    ]


def _quick_toggle_rows(*, toggles: QuickToggleState, actions: MenuActions) -> list[MenuItem]:
    """Fixed mic/DND/dark rows; each is hidden unless its capability is present."""
    return [
        MenuItem(
            label=_("Mute microphone"),
            toggle_type="checkmark",
            toggle_state=TOGGLE_ON if toggles.mic_muted else TOGGLE_OFF,
            visible=toggles.mic_available,
            action=actions.toggle_microphone,
        ),
        MenuItem(label=_("Microphone in use"), enabled=False, visible=toggles.mic_in_use),
        MenuItem(
            label=_("Do not disturb"),
            toggle_type="checkmark",
            toggle_state=TOGGLE_ON if toggles.dnd_active else TOGGLE_OFF,
            visible=toggles.dnd_available,
            action=actions.toggle_dnd,
        ),
        MenuItem(
            label=_("Dark mode"),
            toggle_type="checkmark",
            toggle_state=TOGGLE_ON if toggles.dark_active else TOGGLE_OFF,
            visible=toggles.dark_available,
            action=actions.toggle_dark_mode,
        ),
    ]
