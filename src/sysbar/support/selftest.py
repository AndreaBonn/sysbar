"""Capability and service diagnostics, printed by ``sysbar --selftest``."""

from __future__ import annotations

from .. import __version__
from ..core.capabilities import Capabilities

# Which features each capability gates, for an actionable report.
_FEATURE_HINTS: dict[str, str] = {
    "session_x11": "auto-quit, global hotkeys, shelf shake-to-open",
    "appindicator": "tray icon",
    "sensors": "CPU/GPU temperatures",
    "nvml": "NVIDIA GPU temp/load",
    "pipewire_pulse": "per-app volume mixer",
    "logind": "keep awake, closed-lid",
    "upower": "battery protection, battery metric",
    "polkit": "system package uninstall",
}


def run_selftest(capabilities: Capabilities | None = None) -> str:
    """Return a human-readable capability report.

    Parameters
    ----------
    capabilities
        Pre-built capabilities object (for testing); a fresh one is probed if omitted.
    """
    if capabilities is None:
        capabilities = Capabilities()
        capabilities.refresh()
    state = capabilities.snapshot()

    lines = [f"Sysbar {__version__} self-test", ""]
    for name in _FEATURE_HINTS:
        available = state.get(name, False)
        mark = "ok " if available else "-- "
        lines.append(f"  [{mark}] {name:<16} {_FEATURE_HINTS[name]}")

    missing = [name for name, ok in state.items() if not ok]
    lines.append("")
    if missing:
        lines.append(f"Degraded features depend on: {', '.join(missing)}")
    else:
        lines.append("All capabilities available.")
    return "\n".join(lines)
