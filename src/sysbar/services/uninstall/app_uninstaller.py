"""Uninstaller orchestration (port of ``AppUninstaller``).

Drives the scan → results → removing → done workflow. User residue is always
moved to the trash (reversible, never ``rm``); system package removal is
optional, gated on polkit and never applied to manual installs. Trash, package
remover and scan home are injected, so the workflow is unit-tested.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import ClassVar

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GObject  # noqa: E402

from .leftover_scanner import scan_leftovers  # noqa: E402
from .models import AppTarget, Leftover, PackageManager, Phase, RemovalResult  # noqa: E402
from .ports import PackageRemover, Trash  # noqa: E402

log = logging.getLogger(__name__)


class AppUninstaller(GObject.Object):
    """Scan and remove an application's residue and package."""

    __gsignals__: ClassVar[dict[str, tuple[object, ...]]] = {
        "phase-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(
        self, home: Path, trash: Trash, remover: PackageRemover, polkit_available: bool
    ) -> None:
        super().__init__()
        self._home = home
        self._trash = trash
        self._remover = remover
        self._polkit_available = polkit_available
        self._phase = Phase.EMPTY
        self._target: AppTarget | None = None
        self._leftovers: list[Leftover] = []

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def leftovers(self) -> list[Leftover]:
        return list(self._leftovers)

    def can_remove_package(self, target: AppTarget) -> bool:
        return (
            target.manager is not PackageManager.MANUAL
            and target.package_ref is not None
            and self._polkit_available
        )

    def scan(self, target: AppTarget) -> list[Leftover]:
        self._target = target
        self._set_phase(Phase.SCANNING)
        self._leftovers = scan_leftovers(target.name, target.app_id, self._home)
        self._set_phase(Phase.RESULTS)
        return self.leftovers

    def remove(self, selected: list[Leftover], remove_package: bool) -> RemovalResult:
        self._set_phase(Phase.REMOVING)
        freed = 0
        failed: list[str] = []
        for leftover in selected:
            if self._trash.trash(leftover.path):
                freed += leftover.size_bytes
            else:
                failed.append(leftover.path)
        if remove_package and self._target is not None and self.can_remove_package(self._target):
            ref = self._target.package_ref or ""
            if not self._remover.remove(self._target.manager, ref):
                failed.append(ref)
        self._set_phase(Phase.DONE)
        return RemovalResult(freed_bytes=freed, failed=failed)

    def _set_phase(self, phase: Phase) -> None:
        self._phase = phase
        self.emit("phase-changed", phase.value)
