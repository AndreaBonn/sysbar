"""Tray panel window.

A borderless window kept above other windows, shown next to the tray icon. The
System, Network, Power and Fan sections are populated live from the monitor
snapshot; the Mixer section is driven by the audio service.
"""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from ...app.panel_summary import PanelSummary, QuickTile  # noqa: E402
from ...core.branding import has_app_icon  # noqa: E402
from ...core.constants import APP_ICON_NAME  # noqa: E402
from ...core.i18n import _  # noqa: E402
from ...services.audio.app_volume_mixer import AppVolumeMixer  # noqa: E402
from ...services.audio.device_switcher import DeviceSwitcher  # noqa: E402
from ...services.metrics import metric_format as mf  # noqa: E402
from ...services.system_monitor.history import MetricHistory  # noqa: E402
from ...services.system_monitor.net_per_process import ProcNetRate  # noqa: E402
from ...services.system_monitor.processes import ProcessUsage  # noqa: E402
from ...services.system_monitor.snapshot import SystemSnapshot  # noqa: E402
from .device_section import DeviceSection  # noqa: E402
from .metrics_section import MetricsSection  # noqa: E402
from .mixer_section import MixerSection  # noqa: E402
from .overview_section import OverviewSection, TileCallback  # noqa: E402

KillCallback = Callable[[int, str], None]

_PANEL_WIDTH = 380
_PANEL_HEIGHT = 560
_HEADER_LOGO_PIXELS = 20


def _title_widget() -> Gtk.Widget:
    """Header title: the branded logo next to the app name.

    The logo is shown only when the icon resolves; otherwise the plain name is
    used, so a checkout without a generated icon shows no broken-image glyph.
    """
    label = Gtk.Label(label="Sysbar")
    if not has_app_icon(Gdk.Display.get_default()):
        return label
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    logo = Gtk.Image.new_from_icon_name(APP_ICON_NAME)
    logo.set_pixel_size(_HEADER_LOGO_PIXELS)
    box.append(logo)
    box.append(label)
    return box


class PanelWindow(Adw.Window):
    """The popover-style panel anchored to the tray."""

    def __init__(self) -> None:
        super().__init__(title="Sysbar", decorated=False, resizable=False)
        self.set_default_size(_PANEL_WIDTH, _PANEL_HEIGHT)
        self._overview = OverviewSection()
        self._metrics = MetricsSection()
        self._on_open_settings: Callable[[], None] | None = None
        self._device_section = DeviceSection()
        self._mixer_section = MixerSection()
        self._fan_group = Adw.PreferencesGroup(title=_("Fan Control (beta)"), visible=False)
        self._fan_rows: list[Adw.ActionRow] = []
        self._process_group = Adw.PreferencesGroup(title=_("Top processes"), visible=False)
        self._process_rows: list[Adw.ActionRow] = []
        self._net_group = Adw.PreferencesGroup(title=_("Network by process"), visible=False)
        self._net_rows: list[Adw.ActionRow] = []
        self._on_kill: KillCallback | None = None
        self._build_content()

    def set_temperature_unit(self, unit: str) -> None:
        self._metrics.temperature_unit = unit

    def bind_overview(self, on_tile: TileCallback, on_open_settings: Callable[[], None]) -> None:
        """Route quick-toggle clicks and the header's Preferences button."""
        self._overview.bind_tiles(on_tile)
        self._on_open_settings = on_open_settings

    def set_summary(self, summary: PanelSummary) -> None:
        self._overview.set_summary(summary)

    def set_tiles(self, tiles: list[QuickTile]) -> None:
        self._overview.set_tiles(tiles)

    def set_show_fans(self, show: bool) -> None:
        self._fan_group.set_visible(show)

    def bind_mixer(self, mixer: AppVolumeMixer) -> None:
        self._mixer_section.bind(mixer)

    def bind_devices(self, switcher: DeviceSwitcher) -> None:
        self._device_section.bind(switcher)

    def set_mixer_unavailable(self) -> None:
        self._mixer_section.set_unavailable()

    def bind_process_actions(self, on_kill: KillCallback) -> None:
        """Register the callback invoked when a process row's End button is hit."""
        self._on_kill = on_kill

    def _build_content(self) -> None:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar(show_start_title_buttons=False)
        header.set_title_widget(_title_widget())
        settings = Gtk.Button(icon_name="emblem-system-symbolic", tooltip_text=_("Preferences"))
        settings.connect("clicked", self._on_settings_clicked)
        header.pack_end(settings)
        toolbar.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for margin in ("top", "bottom", "start", "end"):
            getattr(content, f"set_margin_{margin}")(12)
        for section in (
            self._overview,
            self._metrics,
            self._fan_group,
            self._process_group,
            self._net_group,
            self._device_section,
            self._mixer_section,
        ):
            content.append(section)

        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(content)
        toolbar.set_content(scroller)
        self.set_content(toolbar)

    def _on_settings_clicked(self, _button: Gtk.Button) -> None:
        if self._on_open_settings is not None:
            self._on_open_settings()

    def set_graph_metrics(self, enabled: frozenset[str]) -> None:
        """Set which metrics show a sparkline; hides the rest immediately."""
        self._metrics.set_graph_metrics(enabled)

    def update_history(self, history: MetricHistory) -> None:
        """Refresh every enabled sparkline from the recorded history."""
        self._metrics.update_history(history)

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Refresh all metric rows; rows without data are hidden."""
        self._metrics.update_snapshot(snapshot)
        self._update_fans(snapshot.fans)

    def _update_fans(self, fans: dict[str, float]) -> None:
        for row in self._fan_rows:
            self._fan_group.remove(row)
        self._fan_rows.clear()
        for name, rpm in fans.items():
            row = Adw.ActionRow(title=name, subtitle=f"{rpm:.0f} RPM")
            self._fan_group.add(row)
            self._fan_rows.append(row)

    def update_processes(self, processes: list[ProcessUsage]) -> None:
        """Rebuild the top-process rows; each carries an End button."""
        for row in self._process_rows:
            self._process_group.remove(row)
        self._process_rows.clear()
        self._process_group.set_visible(bool(processes))
        for process in processes:
            self._process_group.add(self._process_row(process))

    def _process_row(self, process: ProcessUsage) -> Adw.ActionRow:
        cpu = mf.format_percent(process.cpu_percent)
        memory = mf.format_bytes(process.memory_bytes)
        row = Adw.ActionRow(title=process.name or _("Unknown"), subtitle=f"{cpu} CPU · {memory}")
        button = Gtk.Button(
            icon_name="process-stop-symbolic",
            tooltip_text=_("End process"),
            valign=Gtk.Align.CENTER,
        )
        button.add_css_class("flat")
        button.connect("clicked", self._on_kill_clicked, process.pid, process.name)
        row.add_suffix(button)
        self._process_rows.append(row)
        return row

    def _on_kill_clicked(self, _button: Gtk.Button, pid: int, name: str) -> None:
        if self._on_kill is not None:
            self._on_kill(pid, name)

    def update_net_processes(self, rates: list[ProcNetRate]) -> None:
        """Rebuild the per-process network rows; hidden when there is no traffic."""
        for row in self._net_rows:
            self._net_group.remove(row)
        self._net_rows.clear()
        self._net_group.set_visible(bool(rates))
        for rate in rates:
            subtitle = f"↓{mf.format_rate(rate.rx_rate)} ↑{mf.format_rate(rate.tx_rate)}"
            row = Adw.ActionRow(title=rate.name or _("Unknown"), subtitle=subtitle)
            self._net_group.add(row)
            self._net_rows.append(row)
