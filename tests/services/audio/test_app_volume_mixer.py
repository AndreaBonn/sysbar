from collections.abc import Callable

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib  # noqa: E402

from sysbar.services.audio.app_volume_mixer import AppVolumeMixer  # noqa: E402
from sysbar.services.audio.models import SinkInput  # noqa: E402


class FakeBackend:
    def __init__(self, sink_inputs: list[SinkInput]) -> None:
        self._sink_inputs = sink_inputs
        self.volume_calls: list[tuple[int, float]] = []
        self.mute_calls: list[tuple[int, bool]] = []
        self.callback: Callable[[], None] | None = None

    def list_sink_inputs(self) -> list[SinkInput]:
        return list(self._sink_inputs)

    def set_sink_inputs(self, sink_inputs: list[SinkInput]) -> None:
        self._sink_inputs = sink_inputs

    def set_volume(self, index: int, volume: float) -> None:
        self.volume_calls.append((index, volume))

    def set_mute(self, index: int, muted: bool) -> None:
        self.mute_calls.append((index, muted))

    def subscribe(self, callback: Callable[[], None]) -> None:
        self.callback = callback


def _drain_idle() -> None:
    context = GLib.MainContext.default()
    while context.pending():
        context.iteration(may_block=False)


class FakeStore:
    def __init__(self, volumes: dict[str, float] | None = None) -> None:
        self._volumes = dict(volumes or {})

    def get_app_volumes(self) -> dict[str, float]:
        return dict(self._volumes)

    def set_app_volume(self, app_id: str, volume: float) -> None:
        self._volumes[app_id] = volume


def test_refresh_groups_and_exposes_apps() -> None:
    backend = FakeBackend([SinkInput(index=1, app_id="org.app", name="App", volume=0.5)])
    mixer = AppVolumeMixer(backend, FakeStore())
    mixer.refresh()
    assert [app.id for app in mixer.apps] == ["org.app"]


def test_set_app_volume_fans_out_and_persists() -> None:
    backend = FakeBackend(
        [
            SinkInput(index=1, app_id="org.app", name="App"),
            SinkInput(index=2, app_id="org.app", name="App"),
        ]
    )
    store = FakeStore()
    mixer = AppVolumeMixer(backend, store)
    mixer.refresh()
    mixer.set_app_volume("org.app", 1.5)
    assert backend.volume_calls == [(1, 1.5), (2, 1.5)]
    assert store.get_app_volumes() == {"org.app": 1.5}
    assert mixer.apps[0].volume == 1.5


def test_set_app_muted_fans_out() -> None:
    backend = FakeBackend([SinkInput(index=1, app_id="org.app")])
    mixer = AppVolumeMixer(backend, FakeStore())
    mixer.refresh()
    mixer.set_app_muted("org.app", True)
    assert backend.mute_calls == [(1, True)]
    assert mixer.apps[0].muted is True


def test_set_volume_unknown_app_is_noop() -> None:
    backend = FakeBackend([SinkInput(index=1, app_id="org.app")])
    mixer = AppVolumeMixer(backend, FakeStore())
    mixer.refresh()
    mixer.set_app_volume("nope", 1.5)
    assert backend.volume_calls == []


def test_persisted_volume_reapplied_when_app_first_seen() -> None:
    backend = FakeBackend([SinkInput(index=1, app_id="org.app", volume=1.0)])
    mixer = AppVolumeMixer(backend, FakeStore({"org.app": 0.3}))
    mixer.refresh()
    assert backend.volume_calls == [(1, 0.3)]
    assert mixer.apps[0].volume == 0.3


def test_persisted_volume_not_reapplied_on_subsequent_refresh() -> None:
    backend = FakeBackend([SinkInput(index=1, app_id="org.app", volume=1.0)])
    mixer = AppVolumeMixer(backend, FakeStore({"org.app": 0.3}))
    mixer.refresh()
    backend.volume_calls.clear()
    mixer.refresh()
    assert backend.volume_calls == []


def test_start_subscribes_and_does_initial_refresh() -> None:
    backend = FakeBackend([SinkInput(index=1, app_id="org.app")])
    mixer = AppVolumeMixer(backend, FakeStore())
    mixer.start()
    assert backend.callback is not None
    assert [app.id for app in mixer.apps] == ["org.app"]


def test_set_muted_unknown_app_is_noop() -> None:
    backend = FakeBackend([SinkInput(index=1, app_id="org.app")])
    mixer = AppVolumeMixer(backend, FakeStore())
    mixer.refresh()
    mixer.set_app_muted("nope", True)
    assert backend.mute_calls == []


def test_persisted_volume_within_epsilon_is_not_reapplied() -> None:
    # Stored 0.505 vs live 0.5: closer than the epsilon, so no redundant write.
    backend = FakeBackend([SinkInput(index=1, app_id="org.app", volume=0.5)])
    mixer = AppVolumeMixer(backend, FakeStore({"org.app": 0.505}))
    mixer.refresh()
    assert backend.volume_calls == []
    assert mixer.apps[0].volume == 0.5


def test_backend_event_triggers_refresh_on_idle() -> None:
    backend = FakeBackend([SinkInput(index=1, app_id="org.app")])
    mixer = AppVolumeMixer(backend, FakeStore())
    mixer.start()
    backend.set_sink_inputs([SinkInput(index=2, app_id="org.other")])
    assert backend.callback is not None
    backend.callback()  # schedules a refresh on the GLib idle queue
    _drain_idle()
    assert [app.id for app in mixer.apps] == ["org.other"]
