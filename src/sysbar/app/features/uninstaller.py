"""The application uninstaller and its window."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ...core.capabilities import POLKIT
from ...services.uninstall.app_uninstaller import AppUninstaller
from ...services.uninstall.command_query import CommandPackageQuery
from ...services.uninstall.package_remover import PkexecPackageRemover
from ...services.uninstall.trash import GioTrash
from ..context import AppContext
from ..windows import WindowSlot

if TYPE_CHECKING:
    from ...ui.uninstall.uninstaller_window import UninstallerWindow


class UninstallerFeature:
    """Owns the uninstaller service and its window."""

    def __init__(self, context: AppContext) -> None:
        self._uninstaller = AppUninstaller(
            home=Path.home(),
            trash=GioTrash(),
            remover=PkexecPackageRemover(),
            polkit_available=context.has(POLKIT),
        )
        self._window: WindowSlot[UninstallerWindow] = WindowSlot(self._build_window)

    def open(self) -> None:
        self._window.present()

    def _build_window(self) -> UninstallerWindow:
        from ...ui.uninstall.uninstaller_window import UninstallerWindow

        return UninstallerWindow(self._uninstaller, CommandPackageQuery())
