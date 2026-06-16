"""Named constants for Sysbar.

Every threshold, interval and path used across the codebase is declared here so
that no magic value appears inline (see code-standards.md).
"""

from __future__ import annotations

from pathlib import Path

APP_ID = "it.linkalab.Sysbar"
APP_NAME = "Sysbar"
BINARY_NAME = "sysbar"
GETTEXT_DOMAIN = "sysbar"
GSETTINGS_PATH = "/it/linkalab/Sysbar/"

# Tray icon. A themed symbolic name is used so the icon is visible in a source
# checkout; packaging installs the branded "it.linkalab.Sysbar" icon (M9).
TRAY_ICON_NAME = "utilities-system-monitor-symbolic"
TRAY_TITLE = "Sysbar"

# GitHub identity used by the optional update check (services/update_service.py).
GITHUB_OWNER = "linkalab"
GITHUB_REPO = "sysbar"

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

# Battery watchdog polling cadence for keep-awake.
BATTERY_WATCHDOG_INTERVAL_SECONDS = 45

# Default top-N processes shown for a given resource.
TOP_PROCESS_COUNT = 5

# User data directory for shelf staging and manifest.
DATA_HOME = Path.home() / ".local" / "share" / BINARY_NAME
SHELF_DIR = DATA_HOME / "shelf"
SHELF_MANIFEST = SHELF_DIR / "manifest.json"

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
