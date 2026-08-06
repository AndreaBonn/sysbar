"""Constants of the scenes domain.

Split out of ``core/constants.py`` when that file outgrew the project's line
cap. They are grouped here rather than anywhere else because every one of them
is read by this package or by the tray code that renders it, and none of them
means anything outside it.
"""

from __future__ import annotations

from ...core.constants import DATA_HOME

# Scene rows in the tray submenu. A fixed pool: with user-defined scenes the
# count varies, and a varying node count desynchronises the dbusmenu host, which
# assigns ids by position. Scenes past this limit stay reachable from the
# command line and the palette, just not from the tray.
MAX_SCENE_ROWS = 8

# Settings keys a scene is allowed to write. A whitelist rather than the whole
# schema: a scene is a convenience, not an alternative way to reconfigure the
# application, and letting one write any key would make a hand-edited manifest
# able to change anything at all.
SCENE_WRITABLE_KEYS: frozenset[str] = frozenset(
    {
        "alert-enabled",
        "alert-battery-percent",
        "clamshell-preferred",
        "default-duration-minutes",
        "monitor-interval-seconds",
        "show-countdown",
    }
)

# User scenes and their triggers, in one document: one atomic write, and no
# window in which a trigger points at a scene that is not saved yet.
SCENES_DIR = DATA_HOME / "scenes"
SCENES_MANIFEST = SCENES_DIR / "manifest.json"
SCENES_MANIFEST_VERSION = 1
# The manifest decides what the application does when a scene is activated, so
# it is readable and writable by its owner only.
SCENES_MANIFEST_MODE = 0o600

# Shortest gap between two trigger-driven scene activations. A backstop against
# a source reporting nonsense: the engine is already idempotent on repeated
# state, so in normal operation this never fires.
TRIGGER_MIN_INTERVAL_SECONDS = 10.0
# Hotplugging one monitor emits several display changes in a row, so the source
# waits for them to settle before reporting.
MONITOR_DEBOUNCE_MS = 2000
