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
from gi.repository import Adw, Gtk  # noqa: E402

from ...core.constants import DEFAULT_TEMPERATURE_UNIT  # noqa: E402
from ...core.i18n import _  # noqa: E402
from ...services.audio.app_volume_mixer import AppVolumeMixer  # noqa: E402
from ...services.metrics import metric_format as mf  # noqa: E402
from ...services.system_monitor.processes import ProcessUsage  # noqa: E402
from ...services.system_monitor.snapshot import SystemSnapshot  # noqa: E402
from .mixer_section import MixerSection  # noqa: E402

KillCallback = Callable[[int, str], None]

_PANEL_WIDTH = 380
_PANEL_HEIGHT = 560


class PanelWindow(Adw.Window):
    """The popover-style panel anchored to the tray."""

    def __init__(self) -> None:
        super().__init__(title="Sysbar", decorated=False, resizable=False)
        self.set_default_size(_PANEL_WIDTH, _PANEL_HEIGHT)
        self._temperature_unit = DEFAULT_TEMPERATURE_UNIT
        self._rows: dict[str, Adw.ActionRow] = {}
        self._mixer_section = MixerSection()
        self._fan_group = Adw.PreferencesGroup(title=_("Fan Control (beta)"), visible=False)
        self._fan_rows: list[Adw.ActionRow] = []
        self._process_group = Adw.PreferencesGroup(title=_("Top processes"), visible=False)
        self._process_rows: list[Adw.ActionRow] = []
        self._on_kill: KillCallback | None = None
        self._build_content()

    def set_temperature_unit(self, unit: str) -> None:
        self._temperature_unit = unit

    def set_show_fans(self, show: bool) -> None:
        self._fan_group.set_visible(show)

    def bind_mixer(self, mixer: AppVolumeMixer) -> None:
        self._mixer_section.bind(mixer)

    def set_mixer_unavailable(self) -> None:
        self._mixer_section.set_unavailable()

    def bind_process_actions(self, on_kill: KillCallback) -> None:
        """Register the callback invoked when a process row's End button is hit."""
        self._on_kill = on_kill

    def _build_content(self) -> None:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar(show_start_title_buttons=False)
        header.set_title_widget(Gtk.Label(label="Sysbar"))
        toolbar.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for margin in ("top", "bottom", "start", "end"):
            getattr(content, f"set_margin_{margin}")(12)

        content.append(
            self._group(
                _("System"),
                (
                    ("cpu", "CPU load"),
                    ("cpu_temp", "CPU temperature"),
                    ("gpu", "GPU"),
                    ("memory", "Memory"),
                    ("uptime", "Uptime"),
                ),
            )
        )
        content.append(self._group(_("Network"), (("net_speed", "Speed"), ("net_total", "Total"))))
        content.append(self._group(_("Power"), (("battery", "Battery"), ("power", "Power draw"))))
        content.append(self._fan_group)
        content.append(self._process_group)
        content.append(self._mixer_section)

        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(content)
        toolbar.set_content(scroller)
        self.set_content(toolbar)

    def _group(self, title: str, rows: tuple[tuple[str, str], ...]) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=title)
        for key, label in rows:
            row = Adw.ActionRow(title=label, subtitle="--")
            self._rows[key] = row
            group.add(row)
        return group

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Refresh all metric rows; rows without data are hidden."""
        self._set("cpu", _percent(snapshot.cpu_percent))
        self._set("cpu_temp", self._temp(snapshot.cpu_temp_celsius))
        self._set("gpu", _percent(snapshot.gpu_percent))
        self._set("memory", self._memory_text(snapshot))
        self._set("uptime", _uptime(snapshot.uptime_seconds))
        self._set("net_speed", _net_pair(snapshot.net_rx_rate, snapshot.net_tx_rate, rate=True))
        self._set("net_total", _net_pair(snapshot.net_rx_total, snapshot.net_tx_total, rate=False))
        self._set("battery", _battery_text(snapshot))
        self._set(
            "power", f"{snapshot.power_watts:.0f} W" if snapshot.power_watts is not None else None
        )
        self._update_fans(snapshot.fans)

    def _temp(self, celsius: float | None) -> str | None:
        return (
            mf.format_temperature(celsius, self._temperature_unit) if celsius is not None else None
        )

    @staticmethod
    def _memory_text(snapshot: SystemSnapshot) -> str | None:
        if snapshot.memory_percent is None:
            return None
        percent = mf.format_percent(snapshot.memory_percent)
        return f"{percent} ({snapshot.memory_pressure})" if snapshot.memory_pressure else percent

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

    def _set(self, key: str, value: str | None) -> None:
        row = self._rows[key]
        if value is None:
            row.set_visible(False)
            return
        row.set_visible(True)
        row.set_subtitle(value)


def _percent(value: float | None) -> str | None:
    return mf.format_percent(value) if value is not None else None


def _uptime(seconds: float | None) -> str | None:
    return mf.format_uptime(seconds) if seconds is not None else None


def _battery_text(snapshot: SystemSnapshot) -> str | None:
    if snapshot.battery_percent is None:
        return None
    percent = mf.format_percent(snapshot.battery_percent)
    if snapshot.battery_charging:
        return f"{percent} (charging)"
    if snapshot.on_battery:
        return f"{percent} (on battery)"
    return percent


def _net_pair(rx: float | None, tx: float | None, rate: bool) -> str | None:
    if rx is None or tx is None:
        return None
    fmt = mf.format_rate if rate else mf.format_bytes
    return f"↓{fmt(rx)} ↑{fmt(tx)}"
