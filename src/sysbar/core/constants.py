"""Named constants for Sysbar.

Every threshold, interval and path used across the codebase is declared here so
that no magic value appears inline (see code-standards.md).
"""

from __future__ import annotations

from pathlib import Path

APP_ID = "io.github.AndreaBonn.Sysbar"
APP_NAME = "Sysbar"
BINARY_NAME = "sysbar"
GETTEXT_DOMAIN = "sysbar"
GSETTINGS_PATH = "/io/github/AndreaBonn/Sysbar/"

# Tray icon. A themed symbolic name is used so the icon is visible in a source
# checkout; packaging installs the branded "io.github.AndreaBonn.Sysbar" icon (M9).
TRAY_ICON_NAME = "utilities-system-monitor-symbolic"
TRAY_TITLE = "Sysbar"

# GitHub identity used by the optional update check (services/update_service.py).
GITHUB_OWNER = "AndreaBonn"
GITHUB_REPO = "sysbar"

# Author credit shown in window footers and at the bottom of the tray menu.
AUTHOR_NAME = "Andrea Bonacci"
AUTHOR_GITHUB_URL = f"https://github.com/{GITHUB_OWNER}"

# Keep-awake durations, in minutes (0 = indefinite).
ALLOWED_DURATIONS: tuple[int, ...] = (0, 15, 30, 60, 120, 240, 480)
DEFAULT_DURATION_MINUTES = 0

# Battery cut-off thresholds for keep-awake, in percent (0 = never).
ALLOWED_BATTERY_LIMITS: tuple[int, ...] = (0, 5, 10, 15, 20)
DEFAULT_BATTERY_LIMIT_PERCENT = 10

# System monitor sampling cadence, in seconds.
ALLOWED_INTERVALS: tuple[int, ...] = (1, 2, 5)
DEFAULT_MONITOR_INTERVAL_SECONDS = 2

# Per-application audio volume range (1.0 = 100%, above = boost).
MIN_APP_VOLUME = 0.0
MAX_APP_VOLUME = 2.0

MEMORY_STYLE_DOT = "dot"
MEMORY_STYLE_PERCENT = "percent"
MEMORY_STYLE_BOTH = "both"
ALLOWED_MEMORY_STYLES: tuple[str, ...] = (
    MEMORY_STYLE_DOT,
    MEMORY_STYLE_PERCENT,
    MEMORY_STYLE_BOTH,
)
DEFAULT_MEMORY_STYLE = MEMORY_STYLE_PERCENT

# Per-metric tray placement: hidden, in the always-visible bar, or in the menu.
PLACEMENT_OFF = "off"
PLACEMENT_BAR = "bar"
PLACEMENT_MENU = "menu"
ALLOWED_PLACEMENTS: tuple[str, ...] = (PLACEMENT_OFF, PLACEMENT_BAR, PLACEMENT_MENU)
DEFAULT_PLACEMENT = PLACEMENT_OFF

# Tray metric identifiers, in display order. Each has a "menu-bar-<id>-placement"
# GSettings key and (for migration) a legacy boolean "menu-bar-<id>" key.
TRAY_METRICS: tuple[str, ...] = ("cpu", "gpu", "memory", "network", "battery", "power")

# Metrics that depend on optional hardware: absent on machines without that
# sensor, so their placement is disabled in Settings when no data is present.
# cpu/memory are universal; network is merely transient (no baseline on the
# first sample), so neither is disabled.
HARDWARE_OPTIONAL_METRICS: tuple[str, ...] = ("gpu", "battery", "power")

# Metrics that carry an optional history sparkline in the panel. Each has a
# "monitor-graph-<id>" GSettings key. Order matches the schema declaration.
GRAPH_METRICS: tuple[str, ...] = ("cpu", "gpu", "memory", "network", "power", "battery")

# Number of samples retained per metric for the panel sparklines (a ring buffer).
# At the default 2s cadence this is four minutes of history.
HISTORY_MAX_SAMPLES = 120

TEMPERATURE_CELSIUS = "celsius"
TEMPERATURE_FAHRENHEIT = "fahrenheit"
ALLOWED_TEMPERATURE_UNITS: tuple[str, ...] = (TEMPERATURE_CELSIUS, TEMPERATURE_FAHRENHEIT)
DEFAULT_TEMPERATURE_UNIT = TEMPERATURE_CELSIUS

# Memory pressure thresholds on PSI "some avg10" (see SystemMonitor §5.1).
MEMORY_PRESSURE_WARNING = 10.0
MEMORY_PRESSURE_CRITICAL = 40.0

# Panel sections, in default order.
SECTION_SYSTEM = "system"
SECTION_NETWORK = "network"
SECTION_POWER = "power"
SECTION_MIXER = "mixer"
SECTION_FAN_CONTROL = "fan_control"
PANEL_SECTION_ORDER: tuple[str, ...] = (
    SECTION_SYSTEM,
    SECTION_NETWORK,
    SECTION_POWER,
    SECTION_MIXER,
    SECTION_FAN_CONTROL,
)

# Feature tour versioning (post-update showcase).
CURRENT_FEATURE_SET = 4
PANEL_NAVIGATION_FEATURE_SET = 4

# Capability re-check cadence for dynamic capabilities (session, extension).
CAPABILITY_REFRESH_INTERVAL_SECONDS = 5

# Auto-quit: grace period after the last window closes before terminating.
AUTO_QUIT_GRACE_SECONDS = 2.0
# Escalation delay from SIGTERM to SIGKILL.
AUTO_QUIT_KILL_TIMEOUT_SECONDS = 5.0
DEFAULT_AUTO_QUIT_EXCEPTIONS: tuple[str, ...] = ("org.gnome.Nautilus",)
# System processes that auto-quit must never terminate, regardless of settings.
AUTO_QUIT_SYSTEM_WHITELIST: frozenset[str] = frozenset(
    {
        "gnome-shell",
        "org.gnome.Shell",
        "gnome-session-binary",
        "gnome-session",
        "Xorg",
        "Xwayland",
        "plasmashell",
        APP_ID,
        BINARY_NAME,
    }
)

# Battery watchdog polling cadence for keep-awake.
BATTERY_WATCHDOG_INTERVAL_SECONDS = 45

# Default top-N processes shown for a given resource.
TOP_PROCESS_COUNT = 5

# Top-N processes listed in the panel, with a kill action.
PANEL_PROCESS_COUNT = 5
# Escalation delay from SIGTERM to SIGKILL for a user-requested process kill.
PROCESS_KILL_TIMEOUT_SECONDS = 5.0

# External GNOME desktop schemas driven by the quick toggles. Looked up at
# runtime; absent on non-GNOME sessions, where the toggles hide themselves.
GNOME_INTERFACE_SCHEMA = "org.gnome.desktop.interface"
GNOME_NOTIFICATIONS_SCHEMA = "org.gnome.desktop.notifications"
COLOR_SCHEME_KEY = "color-scheme"
COLOR_SCHEME_DARK = "prefer-dark"
COLOR_SCHEME_DEFAULT = "default"
SHOW_BANNERS_KEY = "show-banners"

# Global hotkey via the xdg-desktop-portal GlobalShortcuts interface (works on
# both X11 and Wayland). The id is the stable handle the portal persists.
GLOBAL_SHORTCUTS_PORTAL_NAME = "org.freedesktop.portal.Desktop"
KEEP_AWAKE_SHORTCUT_ID = "toggle-keep-awake"
KEEP_AWAKE_SHORTCUT_DESCRIPTION = "Toggle keep awake"

# GNOME Shell extension that feeds window open/close events on Wayland, where
# there is no libwnck. The extension owns this bus name and object.
SHELL_EXTENSION_BUS_NAME = "io.github.AndreaBonn.Sysbar.Shell"
SHELL_EXTENSION_OBJECT_PATH = "/io/github/AndreaBonn/Sysbar/Shell"
SHELL_EXTENSION_INTERFACE = "io.github.AndreaBonn.Sysbar.WindowManager"
SHELL_EXTENSION_UUID = "sysbar-window-manager@andreabonn.github.io"

# System-monitor alert bounds. Percentages are clamped to [0, 100] (0 = the
# alert is off); the sustained-CPU window and the temperature ceiling have their
# own ranges. These cap user input read from GSettings.
ALERT_PERCENT_MIN = 0
ALERT_PERCENT_MAX = 100
ALERT_CPU_SECONDS_MIN = 0
ALERT_CPU_SECONDS_MAX = 3600
DEFAULT_ALERT_CPU_SECONDS = 30
ALERT_TEMPERATURE_MIN = 0
ALERT_TEMPERATURE_MAX = 150

# User data directory for shelf staging and manifest.
DATA_HOME = Path.home() / ".local" / "share" / BINARY_NAME
SHELF_DIR = DATA_HOME / "shelf"
SHELF_MANIFEST = SHELF_DIR / "manifest.json"

# Shake-to-open detection (pointer direction reversals within a time window).
SHAKE_MIN_MOVE_PIXELS = 8.0
SHAKE_WINDOW_SECONDS = 0.6
SHAKE_REQUIRED_REVERSALS = 4
SHAKE_POLL_MS = 30

# Sysfs / procfs paths read by the system monitor.
PROC_STAT = Path("/proc/stat")
PROC_MEMINFO = Path("/proc/meminfo")
PROC_UPTIME = Path("/proc/uptime")
PROC_NET_DEV = Path("/proc/net/dev")
PROC_PRESSURE_MEMORY = Path("/proc/pressure/memory")
POWER_SUPPLY_PATH = Path("/sys/class/power_supply")
HWMON_PATH = Path("/sys/class/hwmon")
DRM_PATH = Path("/sys/class/drm")
RAPL_PATH = Path("/sys/class/powercap/intel-rapl")

# Filesystem whose usage drives the disk metric and the disk-full alert.
ROOT_FILESYSTEM_PATH = Path("/")
