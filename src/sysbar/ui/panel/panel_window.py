"""Tray panel window.

A borderless window kept above other windows, shown next to the tray icon. The
System section is populated live from the monitor snapshot; the remaining
sections are placeholders filled in by later milestones.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ...core.constants import DEFAULT_TEMPERATURE_UNIT  # noqa: E402
from ...services.audio.app_volume_mixer import AppVolumeMixer  # noqa: E402
from ...services.metrics import metric_format as mf  # noqa: E402
from ...services.system_monitor.snapshot import SystemSnapshot  # noqa: E402
from .mixer_section import MixerSection  # noqa: E402

_PANEL_WIDTH = 360
_PANEL_HEIGHT = 480
_PLACEHOLDER_SECTIONS = (("Network", "network"), ("Power", "power"))


class PanelWindow(Adw.Window):
    """The popover-style panel anchored to the tray."""

    def __init__(self) -> None:
        super().__init__(title="Sysbar", decorated=False, resizable=False)
        self.set_default_size(_PANEL_WIDTH, _PANEL_HEIGHT)
        self._temperature_unit = DEFAULT_TEMPERATURE_UNIT
        self._rows: dict[str, Adw.ActionRow] = {}
        self._mixer_section = MixerSection()
        self._build_content()

    def set_temperature_unit(self, unit: str) -> None:
        self._temperature_unit = unit

    def bind_mixer(self, mixer: AppVolumeMixer) -> None:
        self._mixer_section.bind(mixer)

    def set_mixer_unavailable(self) -> None:
        self._mixer_section.set_unavailable()

    def _build_content(self) -> None:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar(show_start_title_buttons=False)
        header.set_title_widget(Gtk.Label(label="Sysbar"))
        toolbar.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for margin in ("top", "bottom", "start", "end"):
            getattr(content, f"set_margin_{margin}")(12)

        content.append(self._build_system_group())
        for title, _key in _PLACEHOLDER_SECTIONS:
            content.append(self._placeholder_group(title))
        content.append(self._mixer_section)

        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(content)
        toolbar.set_content(scroller)
        self.set_content(toolbar)

    def _build_system_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="System")
        for key, title in (
            ("cpu", "CPU load"),
            ("cpu_temp", "CPU temperature"),
            ("memory", "Memory"),
            ("uptime", "Uptime"),
        ):
            row = Adw.ActionRow(title=title, subtitle="--")
            self._rows[key] = row
            group.add(row)
        return group

    def _placeholder_group(self, title: str) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=title)
        group.add(Adw.ActionRow(title="No data yet"))
        return group

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        """Refresh the System rows; rows without data are hidden."""
        self._set_row(
            "cpu",
            mf.format_percent(snapshot.cpu_percent) if snapshot.cpu_percent is not None else None,
        )
        self._set_row(
            "cpu_temp",
            mf.format_temperature(snapshot.cpu_temp_celsius, self._temperature_unit)
            if snapshot.cpu_temp_celsius is not None
            else None,
        )
        self._set_row(
            "memory",
            self._memory_text(snapshot) if snapshot.memory_percent is not None else None,
        )
        self._set_row(
            "uptime",
            mf.format_uptime(snapshot.uptime_seconds)
            if snapshot.uptime_seconds is not None
            else None,
        )

    @staticmethod
    def _memory_text(snapshot: SystemSnapshot) -> str:
        percent = mf.format_percent(snapshot.memory_percent or 0.0)
        if snapshot.memory_pressure:
            return f"{percent} ({snapshot.memory_pressure})"
        return percent

    def _set_row(self, key: str, value: str | None) -> None:
        row = self._rows[key]
        if value is None:
            row.set_visible(False)
            return
        row.set_visible(True)
        row.set_subtitle(value)
