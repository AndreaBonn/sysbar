from __future__ import annotations

from sysbar.services.scenes.models import Scene
from sysbar.services.scenes.service import SceneService

_SCENES = [
    Scene(
        "focus",
        "Focus",
        keep_awake=True,
        do_not_disturb=True,
        mute_microphone=True,
        settings={"alert-enabled": False},
    ),
    Scene(
        "relax",
        "Relax",
        keep_awake=False,
        do_not_disturb=False,
        mute_microphone=False,
        settings={"monitor-interval-seconds": 5},
    ),
]


class FakeWriter:
    def __init__(self) -> None:
        self.written: dict[str, object] = {}

    def set(self, key: str, value: object) -> None:
        self.written[key] = value


class FakeApplier:
    def __init__(self) -> None:
        self.keep_awake: bool | None = None
        self.dnd: bool | None = None
        self.mute: bool | None = None

    def set_keep_awake(self, on: bool) -> None:
        self.keep_awake = on

    def set_do_not_disturb(self, on: bool) -> None:
        self.dnd = on

    def set_microphone_muted(self, on: bool) -> None:
        self.mute = on


def _service() -> tuple[SceneService, FakeWriter, FakeApplier]:
    writer = FakeWriter()
    applier = FakeApplier()
    return SceneService(writer, applier, scenes=_SCENES), writer, applier


def test_activate_writes_scene_settings() -> None:
    service, writer, _ = _service()
    service.activate("focus")
    assert writer.written["alert-enabled"] is False


def test_activate_applies_runtime_toggles() -> None:
    service, _, applier = _service()
    service.activate("focus")
    assert (applier.keep_awake, applier.dnd, applier.mute) == (True, True, True)


def test_activate_records_active_scene() -> None:
    service, writer, _ = _service()
    service.activate("focus")
    assert service.active_id == "focus"
    assert writer.written["active-scene"] == "focus"


def test_activate_unknown_scene_is_noop() -> None:
    service, writer, applier = _service()
    service.activate("ghost")
    assert service.active_id == ""
    assert writer.written == {}
    assert applier.keep_awake is None


def test_clear_turns_off_runtime_toggles_and_active_scene() -> None:
    service, writer, applier = _service()
    service.activate("focus")
    service.clear()
    assert (applier.keep_awake, applier.dnd, applier.mute) == (False, False, False)
    assert service.active_id == ""
    assert writer.written["active-scene"] == ""


def test_changed_emitted_on_activate_and_clear() -> None:
    service, _, _ = _service()
    received: list[str] = []
    service.connect("changed", lambda _s: received.append(service.active_id))
    service.activate("relax")
    service.clear()
    assert received == ["relax", ""]


def test_scenes_property_exposes_presets() -> None:
    service, _, _ = _service()
    assert [s.id for s in service.scenes] == ["focus", "relax"]
