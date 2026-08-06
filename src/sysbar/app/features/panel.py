"""The metrics panel: its window, its per-open configuration and its updates.

The panel is the one window that consumes a live stream rather than a snapshot
of state, so it owns how a sample reaches it. Everything it shows comes from two
other features, the monitor for data and audio for the mixer rows, which it
receives rather than builds.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import gi

gi.require_version("Adw", "1")
from gi.repository import Adw  # noqa: E402

from ...core.constants import PANEL_PROCESS_COUNT  # noqa: E402
from ...core.i18n import _  # noqa: E402
from ...services.system_monitor.snapshot import SystemSnapshot  # noqa: E402
from .. import tray_state  # noqa: E402
from ..context import AppContext  # noqa: E402
from ..windows import WindowSlot  # noqa: E402
from .audio import AudioFeature  # noqa: E402
from .monitor import MonitorFeature  # noqa: E402

if TYPE_CHECKING:
    from ...ui.panel.panel_window import PanelWindow

_KILL_CANCEL = "cancel"
_KILL_CONFIRM = "end"
_FAN_CONTROL_KEY = "monitor-show-fan-control-beta"


class PanelFeature:
    """Owns the panel window and the flow of samples into it."""

    def __init__(self, context: AppContext, monitor: MonitorFeature, audio: AudioFeature) -> None:
        self._context = context
        self._monitor = monitor
        self._audio = audio
        self._window: WindowSlot[PanelWindow] = WindowSlot(self._build, self._on_closed)

    def open(self) -> None:
        panel = self._window.present()
        config = self._context.config
        panel.set_temperature_unit(config.temperature_unit)
        panel.set_show_fans(config.get_bool(_FAN_CONTROL_KEY))
        panel.set_graph_metrics(tray_state.graph_metrics(config))
        self._audio.refresh_devices()
        self._monitor.set_panel_open(True)
        snapshot = self._monitor.latest
        if snapshot is not None:
            self._push(panel, snapshot)

    def push_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Feed a fresh sample to the panel, or do nothing if it is closed."""
        self._window.if_open(lambda panel: self._push(panel, snapshot))

    def apply_graph_metrics(self) -> None:
        """Re-apply the sparkline selection after a settings change."""
        self._window.if_open(self._refresh_graphs)

    def _build(self) -> PanelWindow:
        from ...ui.panel.panel_window import PanelWindow

        panel = PanelWindow()
        panel.bind_process_actions(self._confirm_kill)
        self._audio.bind_panel(panel)
        return panel

    def _on_closed(self) -> None:
        self._monitor.set_panel_open(False)

    def _push(self, panel: PanelWindow, snapshot: SystemSnapshot) -> None:
        panel.update_snapshot(snapshot)
        panel.update_history(self._monitor.history)
        panel.update_processes(self._monitor.top_cpu(PANEL_PROCESS_COUNT))
        panel.update_net_processes(self._monitor.net_processes())

    def _refresh_graphs(self, panel: PanelWindow) -> None:
        panel.set_graph_metrics(tray_state.graph_metrics(self._context.config))
        panel.update_history(self._monitor.history)

    def _confirm_kill(self, pid: int, name: str) -> None:
        """Ask before killing; a stray click should not terminate a process."""
        self._window.if_open(lambda panel: self._present_kill_dialog(panel, pid, name))

    def _present_kill_dialog(self, panel: PanelWindow, pid: int, name: str) -> None:
        dialog = Adw.MessageDialog(
            transient_for=panel,
            heading=_("End process?"),
            body=_("Send a termination signal to “{name}” (PID {pid})?").format(name=name, pid=pid),
        )
        dialog.add_response(_KILL_CANCEL, _("Cancel"))
        dialog.add_response(_KILL_CONFIRM, _("End process"))
        dialog.set_response_appearance(_KILL_CONFIRM, Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response(_KILL_CANCEL)
        dialog.set_close_response(_KILL_CANCEL)
        dialog.connect("response", self._on_kill_response, pid)
        dialog.present()

    def _on_kill_response(self, _dialog: Adw.MessageDialog, response: str, pid: int) -> None:
        if response == _KILL_CONFIRM:
            self._monitor.terminate(pid)
