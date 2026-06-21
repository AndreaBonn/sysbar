"""Typed value objects for the system monitor that are not raw snapshots.

Kept separate from :mod:`snapshot` so the pure parsers can import them without
pulling in the full snapshot surface.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PeripheralBattery:
    """Battery reading for one connected peripheral (keyboard, mouse, headset…).

    ``kind`` is the raw UPower device-type code; the renderer maps it to a
    localized name when the device exposes no descriptive ``model``.
    """

    model: str
    kind: int
    percent: float
    charging: bool
