"""XDG autostart management.

Creating or removing ``~/.config/autostart/io.github.AndreaBonn.Sysbar.desktop`` is the
Linux equivalent of a macOS login item. The directory is injectable so the
logic is testable without touching the real home directory.
"""

from __future__ import annotations

from pathlib import Path

from ..core.constants import APP_ID, BINARY_NAME

_DESKTOP_ENTRY = f"""[Desktop Entry]
Type=Application
Name=Sysbar
Comment=Start Sysbar at login
Exec={BINARY_NAME}
Icon={APP_ID}
Terminal=false
Categories=Utility;System;
X-GNOME-Autostart-enabled=true
"""


class AutostartManager:
    """Enable or disable launching Sysbar at login."""

    def __init__(self, autostart_dir: Path | None = None) -> None:
        self._dir = autostart_dir or (Path.home() / ".config" / "autostart")
        self._file = self._dir / f"{APP_ID}.desktop"

    def is_enabled(self) -> bool:
        return self._file.is_file()

    def enable(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file.write_text(_DESKTOP_ENTRY, encoding="utf-8")

    def disable(self) -> None:
        self._file.unlink(missing_ok=True)

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self.enable()
        else:
            self.disable()
