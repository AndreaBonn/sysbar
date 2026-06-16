"""Mixer section of the panel: one row per audio application.

Rows are keyed by app id and diffed on update, so the volume slider the user is
dragging is never rebuilt under them (which would otherwise feed back into a
volume change).
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ...core.constants import MAX_APP_VOLUME, MIN_APP_VOLUME  # noqa: E402
from ...services.audio.app_volume_mixer import AppVolumeMixer  # noqa: E402
from ...services.audio.models import MixerApp  # noqa: E402

_VOLUME_STEP = 0.01
_SLIDER_WIDTH = 140
_PLAYING_ICON = "audio-volume-high-symbolic"
_IDLE_ICON = "audio-volume-muted-symbolic"


class _AppRow:
    """An Adw.ActionRow with a volume slider and a mute toggle for one app."""

    def __init__(self, app: MixerApp, mixer: AppVolumeMixer) -> None:
        self._app_id = app.id
        self._mixer = mixer
        self.row = Adw.ActionRow(title=app.name)
        self._icon = Gtk.Image()
        self.row.add_prefix(self._icon)

        self._scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, MIN_APP_VOLUME, MAX_APP_VOLUME, _VOLUME_STEP
        )
        self._scale.set_size_request(_SLIDER_WIDTH, -1)
        self._scale.set_draw_value(False)
        self._scale.set_value(app.volume)
        self._scale.set_valign(Gtk.Align.CENTER)
        self._scale.connect("value-changed", self._on_volume_changed)
        self.row.add_suffix(self._scale)

        self._mute = Gtk.ToggleButton(icon_name="audio-volume-muted-symbolic")
        self._mute.set_valign(Gtk.Align.CENTER)
        self._mute.set_active(app.muted)
        self._mute.connect("toggled", self._on_mute_toggled)
        self.row.add_suffix(self._mute)

        self.update(app)

    def update(self, app: MixerApp) -> None:
        self._icon.set_from_icon_name(_PLAYING_ICON if app.is_playing else _IDLE_ICON)
        if self._mute.get_active() != app.muted:
            self._mute.set_active(app.muted)

    def _on_volume_changed(self, scale: Gtk.Scale) -> None:
        self._mixer.set_app_volume(self._app_id, scale.get_value())

    def _on_mute_toggled(self, button: Gtk.ToggleButton) -> None:
        self._mixer.set_app_muted(self._app_id, button.get_active())


class MixerSection(Adw.PreferencesGroup):
    """Live list of per-application volume controls."""

    def __init__(self) -> None:
        super().__init__(title="Mixer")
        self._mixer: AppVolumeMixer | None = None
        self._rows: dict[str, _AppRow] = {}
        self._empty = Adw.ActionRow(title="No audio playing")
        self.add(self._empty)

    def set_unavailable(self) -> None:
        self._empty.set_title("PipeWire/PulseAudio not available")

    def bind(self, mixer: AppVolumeMixer) -> None:
        self._mixer = mixer
        mixer.connect("apps-changed", self._on_apps_changed)
        self._rebuild(mixer.apps)

    def _on_apps_changed(self, mixer: AppVolumeMixer) -> None:
        self._rebuild(mixer.apps)

    def _rebuild(self, apps: list[MixerApp]) -> None:
        if self._mixer is None:
            return
        present = {app.id for app in apps}
        for app_id in list(self._rows):
            if app_id not in present:
                self.remove(self._rows.pop(app_id).row)
        for app in apps:
            existing = self._rows.get(app.id)
            if existing is None:
                row = _AppRow(app, self._mixer)
                self._rows[app.id] = row
                self.add(row.row)
            else:
                existing.update(app)
        self._empty.set_visible(not apps)
