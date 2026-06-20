"""Runtime capability detection (the Linux substitute for the macOS TCC model).

Instead of requesting permissions, Sysbar probes for dependencies, extensions
and reachable services, and degrades features that are unavailable. The
:class:`Capabilities` object is observable: the UI subscribes to the ``changed``
signal rather than polling.
"""

from __future__ import annotations

import logging
import os
import shutil
from collections.abc import Callable
from typing import ClassVar

import gi

gi.require_version("GLib", "2.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib, GObject  # noqa: E402

from .constants import (  # noqa: E402
    GLOBAL_SHORTCUTS_PORTAL_NAME,
    GNOME_INTERFACE_SCHEMA,
    GNOME_NOTIFICATIONS_SCHEMA,
    HWMON_PATH,
    SHELL_EXTENSION_BUS_NAME,
)

log = logging.getLogger(__name__)

SESSION_X11 = "session_x11"
APPINDICATOR = "appindicator"
SENSORS = "sensors"
NVML = "nvml"
PIPEWIRE_PULSE = "pipewire_pulse"
LOGIND = "logind"
UPOWER = "upower"
POLKIT = "polkit"
GNOME_DESKTOP = "gnome_desktop"
WAYLAND_WINDOW_SOURCE = "wayland_window_source"
GLOBAL_SHORTCUTS = "global_shortcuts"
PROC_NET_STATS = "proc_net_stats"


def detect_session_x11() -> bool:
    if os.environ.get("WAYLAND_DISPLAY"):
        return False
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "x11"


def detect_appindicator() -> bool:
    return _dbus_name_available(Gio.BusType.SESSION, "org.kde.StatusNotifierWatcher")


def detect_sensors() -> bool:
    if HWMON_PATH.is_dir() and any(HWMON_PATH.iterdir()):
        return True
    return shutil.which("sensors") is not None


def detect_nvml() -> bool:
    try:
        import pynvml

        pynvml.nvmlInit()
        try:
            return bool(pynvml.nvmlDeviceGetCount() > 0)
        finally:
            pynvml.nvmlShutdown()
    except Exception:
        return False


def detect_pipewire_pulse() -> bool:
    try:
        import pulsectl

        with pulsectl.Pulse("sysbar-capability-probe"):
            return True
    except Exception:
        return False


def detect_logind() -> bool:
    return _dbus_name_available(Gio.BusType.SYSTEM, "org.freedesktop.login1")


def detect_upower() -> bool:
    return _dbus_name_available(Gio.BusType.SYSTEM, "org.freedesktop.UPower")


def detect_polkit() -> bool:
    return shutil.which("pkexec") is not None


def detect_gnome_desktop() -> bool:
    """Whether the GNOME schemas the quick toggles drive are installed."""
    source = Gio.SettingsSchemaSource.get_default()
    if source is None:
        return False
    return all(
        source.lookup(schema, True) is not None
        for schema in (GNOME_INTERFACE_SCHEMA, GNOME_NOTIFICATIONS_SCHEMA)
    )


def detect_wayland_window_source() -> bool:
    """Whether the Sysbar GNOME Shell extension is running and exporting events."""
    return _dbus_name_available(Gio.BusType.SESSION, SHELL_EXTENSION_BUS_NAME)


def detect_global_shortcuts() -> bool:
    """Whether the desktop portal that backs global shortcuts is reachable."""
    return _dbus_name_available(Gio.BusType.SESSION, GLOBAL_SHORTCUTS_PORTAL_NAME)


def detect_proc_net_stats() -> bool:
    """Whether ``ss`` is available for per-process network throughput."""
    return shutil.which("ss") is not None


def _dbus_name_available(bus_type: Gio.BusType, name: str) -> bool:
    try:
        bus = Gio.bus_get_sync(bus_type, None)
        result = bus.call_sync(
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "NameHasOwner",
            GLib.Variant("(s)", (name,)),
            GLib.VariantType("(b)"),
            Gio.DBusCallFlags.NONE,
            500,
            None,
        )
        return bool(result.unpack()[0])
    except Exception:
        return False


DETECTORS: dict[str, Callable[[], bool]] = {
    SESSION_X11: detect_session_x11,
    APPINDICATOR: detect_appindicator,
    SENSORS: detect_sensors,
    NVML: detect_nvml,
    PIPEWIRE_PULSE: detect_pipewire_pulse,
    LOGIND: detect_logind,
    UPOWER: detect_upower,
    POLKIT: detect_polkit,
    GNOME_DESKTOP: detect_gnome_desktop,
    WAYLAND_WINDOW_SOURCE: detect_wayland_window_source,
    GLOBAL_SHORTCUTS: detect_global_shortcuts,
    PROC_NET_STATS: detect_proc_net_stats,
}


class Capabilities(GObject.Object):
    """Observable map of capability name to availability."""

    __gsignals__: ClassVar[dict[str, tuple[object, ...]]] = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, detectors: dict[str, Callable[[], bool]] | None = None) -> None:
        super().__init__()
        self._detectors = detectors if detectors is not None else DETECTORS
        self._state: dict[str, bool] = dict.fromkeys(self._detectors, False)

    def has(self, name: str) -> bool:
        """Return whether capability ``name`` is currently available."""
        return self._state.get(name, False)

    def snapshot(self) -> dict[str, bool]:
        """Return a copy of the current capability state."""
        return dict(self._state)

    def refresh(self) -> bool:
        """Re-run all detectors. Emit ``changed`` and return ``True`` if anything flipped."""
        new_state: dict[str, bool] = {}
        for name, detector in self._detectors.items():
            try:
                new_state[name] = detector()
            except Exception:
                log.warning("capability detector failed", extra={"capability": name})
                new_state[name] = False
        changed = new_state != self._state
        self._state = new_state
        if changed:
            self.emit("changed")
        return changed
