"""Per-application volume mixer service (port of ``MixerApp`` orchestration).

Groups live audio streams by application, reapplies persisted volumes when an
app reappears, and exposes set-volume/mute that fan out to every stream of the
app. Observable via the ``apps-changed`` signal. Backend and store are injected.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import ClassVar

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib, GObject  # noqa: E402

from .models import MixerApp, group_sink_inputs  # noqa: E402
from .ports import AudioBackend, VolumeStore  # noqa: E402

log = logging.getLogger(__name__)

_VOLUME_EPSILON = 0.01


class AppVolumeMixer(GObject.Object):
    """Live per-application volume control."""

    __gsignals__: ClassVar[dict[str, tuple[object, ...]]] = {
        "apps-changed": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, backend: AudioBackend, store: VolumeStore) -> None:
        super().__init__()
        self._backend = backend
        self._store = store
        self._apps: list[MixerApp] = []
        self._known_ids: set[str] = set()

    @property
    def apps(self) -> list[MixerApp]:
        return list(self._apps)

    def start(self) -> None:
        self._backend.subscribe(self._on_backend_event)
        self.refresh()

    def refresh(self) -> None:
        apps = group_sink_inputs(self._backend.list_sink_inputs())
        saved = self._store.get_app_volumes()
        self._apps = [self._reapply_if_new(app, saved) for app in apps]
        self._known_ids = {app.id for app in self._apps}
        self.emit("apps-changed")

    def set_app_volume(self, app_id: str, volume: float) -> None:
        app = self._find(app_id)
        if app is None:
            return
        for index in app.sink_input_indices:
            self._backend.set_volume(index, volume)
        self._store.set_app_volume(app_id, volume)
        self._swap(app, dataclasses.replace(app, volume=volume))
        self.emit("apps-changed")

    def set_app_muted(self, app_id: str, muted: bool) -> None:
        app = self._find(app_id)
        if app is None:
            return
        for index in app.sink_input_indices:
            self._backend.set_mute(index, muted)
        self._swap(app, dataclasses.replace(app, muted=muted))
        self.emit("apps-changed")

    def _reapply_if_new(self, app: MixerApp, saved: dict[str, float]) -> MixerApp:
        if app.id in self._known_ids or app.id not in saved:
            return app
        target = saved[app.id]
        if abs(target - app.volume) < _VOLUME_EPSILON:
            return app
        for index in app.sink_input_indices:
            self._backend.set_volume(index, target)
        return dataclasses.replace(app, volume=target)

    def _find(self, app_id: str) -> MixerApp | None:
        return next((app for app in self._apps if app.id == app_id), None)

    def _swap(self, app: MixerApp, updated: MixerApp) -> None:
        self._apps = [updated if other.id == app.id else other for other in self._apps]

    def _on_backend_event(self) -> None:
        GLib.idle_add(self._refresh_idle)

    def _refresh_idle(self) -> bool:
        self.refresh()
        return False
