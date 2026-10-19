"""Choose audio labels, names and selection independently of GTK widgets.

The panel only displays choices and switches devices; default selection and
index validation live here so they can be tested without a display.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..services.audio.models import AudioDevice

_FIRST_DEVICE_INDEX = 0


@dataclass(frozen=True)
class DeviceChoices:
    """Ordered display labels and device names with an optional selection."""

    labels: tuple[str, ...]
    names: tuple[str, ...]
    selected: int | None


def default_choices(devices: list[AudioDevice]) -> DeviceChoices:
    """Build choices, selecting the last default or the first available device.

    Parameters
    ----------
    devices : list[AudioDevice]
        Devices in display order.

    Returns
    -------
    DeviceChoices
        Labels and names in the same order, with no selection for an empty list.
    """
    selected = _FIRST_DEVICE_INDEX if devices else None
    for index, device in enumerate(devices):
        if device.is_default:
            selected = index
    return DeviceChoices(
        labels=tuple(device.description for device in devices),
        names=tuple(device.name for device in devices),
        selected=selected,
    )


def name_at(choices: DeviceChoices, index: int) -> str | None:
    """Resolve a selection without accepting negative or out-of-range indices.

    Parameters
    ----------
    choices : DeviceChoices
        Ordered device choices.
    index : int
        Selected row index.

    Returns
    -------
    str or None
        Device name, or None when the index does not identify a row.
    """
    if _FIRST_DEVICE_INDEX <= index < len(choices.names):
        return choices.names[index]
    return None


def scene_output_choices(devices: list[AudioDevice], selected_name: str | None) -> DeviceChoices:
    """Build scene choices with a neutral name before the connected devices.

    Parameters
    ----------
    devices : list[AudioDevice]
        Connected outputs in display order.
    selected_name : str or None
        Output stored by the scene, which may have been disconnected.

    Returns
    -------
    DeviceChoices
        Device labels only; names include the neutral empty name at index zero.
        The UI prepends its translated neutral label. Selection is always set.
    """
    names = ("", *(device.name for device in devices))
    return DeviceChoices(
        labels=tuple(device.description or device.name for device in devices),
        names=names,
        selected=names.index(selected_name) if selected_name in names else _FIRST_DEVICE_INDEX,
    )
