"""Sysbar: system tray toolkit for Ubuntu/GNOME."""

from importlib.metadata import PackageNotFoundError, version

# Used only when running from a source tree with no installed distribution
# metadata (e.g. a bare checkout). Installed builds and editable dev installs
# resolve the real version from the package metadata, keeping pyproject.toml the
# single source of truth so a release bump never has to touch this file.
_FALLBACK_VERSION = "0.0.0+unknown"


def _resolve_version() -> str:
    try:
        return version("sysbar")
    except PackageNotFoundError:
        return _FALLBACK_VERSION


__version__ = _resolve_version()
