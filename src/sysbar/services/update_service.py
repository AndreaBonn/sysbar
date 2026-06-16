"""Optional update check against the GitHub Releases API.

The only network call Sysbar makes, and it is disabled by ``auto-check-updates``.
Real updates arrive via APT; this just notices a newer release and suggests
upgrading. Version comparison is pure and unit-tested; the HTTP call is the
boundary.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from .. import __version__
from ..core.constants import GITHUB_OWNER, GITHUB_REPO

log = logging.getLogger(__name__)

_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
_VERSION_RE = re.compile(r"\d+")
_REQUEST_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class UpdateInfo:
    """A newer release than the running version."""

    version: str
    url: str


def parse_version(text: str) -> tuple[int, ...]:
    """Parse a version string (``v1.2.3`` or ``1.2.3``) into a comparable tuple."""
    return tuple(int(part) for part in _VERSION_RE.findall(text))


def is_newer(current: str, latest: str) -> bool:
    """Return whether ``latest`` is a strictly newer version than ``current``."""
    return parse_version(latest) > parse_version(current)


class UpdateService:
    """Checks GitHub for a newer release than the running version."""

    def __init__(self, current_version: str = __version__) -> None:
        self._current = current_version

    def check(self) -> UpdateInfo | None:
        """Return update info if a newer release exists, else ``None``."""
        import requests

        try:
            response = requests.get(_RELEASES_URL, timeout=_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            log.info("update check skipped", extra={"error": str(error)})
            return None
        tag = str(payload.get("tag_name", ""))
        if tag and is_newer(self._current, tag):
            return UpdateInfo(version=tag, url=str(payload.get("html_url", "")))
        return None
