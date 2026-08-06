"""Per-feature wiring, one module per feature.

Each module owns the services of one feature, including their capability gating,
and exposes a *total* interface: a feature whose backend is missing answers with
a value or does nothing, it never hands a ``None`` back to its caller. That is
the point of the split. The nullable attributes used to live on the application
object, so every caller carried an ``if ... is not None`` and each new feature
cost lines in several places at once.

Rule of thumb for keeping it that way: a new feature is one module here plus two
lines in ``application.py``, the construction and the settings routing. If it
needs a third, the boundary is in the wrong place.
"""

from __future__ import annotations

from dataclasses import dataclass

from .audio import AudioFeature
from .auto_quit import AutoQuitFeature
from .clipboard import ClipboardFeature
from .keep_awake import KeepAwakeFeature
from .monitor import MonitorFeature
from .panel import PanelFeature
from .scenes import ScenesFeature
from .shelf import ShelfFeature
from .toggles import TogglesFeature
from .uninstaller import UninstallerFeature
from .updates import UpdateCheckFeature


@dataclass(frozen=True)
class Features:
    """Every wired feature, assembled once during application startup.

    One container rather than one attribute per feature on the application: the
    application holds a single "wired yet?" question instead of twenty, and the
    features themselves answer totally from there on.
    """

    monitor: MonitorFeature
    keep_awake: KeepAwakeFeature
    audio: AudioFeature
    panel: PanelFeature
    toggles: TogglesFeature
    scenes: ScenesFeature
    shelf: ShelfFeature
    clipboard: ClipboardFeature
    auto_quit: AutoQuitFeature
    uninstaller: UninstallerFeature
    updates: UpdateCheckFeature
