"""Activating and clearing scenes."""

from __future__ import annotations

from dataclasses import dataclass, field

from sysbar.services.scenes.actions import (
    SetOutputDevice,
    SetSetting,
    SetToggle,
    SystemToggle,
)
from sysbar.services.scenes.apply import ScenePorts, Status
from sysbar.services.scenes.models import Scene, SceneOrigin
from sysbar.services.scenes.service import SceneService


@dataclass
class _FakeToggles:
    supported: set[SystemToggle] = field(default_factory=lambda: set(SystemToggle))
    state: dict[SystemToggle, bool] = field(default_factory=dict)

    def supports(self, toggle: SystemToggle) -> bool:
        return toggle in self.supported

    def set_keep_awake(self, on: bool) -> None:
        self.state[SystemToggle.KEEP_AWAKE] = on

    def set_do_not_disturb(self, on: bool) -> None:
        self.state[SystemToggle.DO_NOT_DISTURB] = on

    def set_microphone_muted(self, on: bool) -> None:
        self.state[SystemToggle.MICROPHONE_MUTED] = on


@dataclass
class _FakeSettings:
    written: dict[str, object] = field(default_factory=dict)

    def set(self, key: str, value: object) -> None:
        self.written[key] = value


@dataclass
class _FakeAudio:
    available: set[str] = field(default_factory=set)
    selected: list[str] = field(default_factory=list)

    def set_output_device(self, device: str) -> bool:
        if device not in self.available:
            return False
        self.selected.append(device)
        return True


_SCENES = [
    Scene(
        id="focus",
        name="Focus",
        actions=(
            SetToggle(toggle=SystemToggle.KEEP_AWAKE, value=True),
            SetToggle(toggle=SystemToggle.DO_NOT_DISTURB, value=True),
            SetToggle(toggle=SystemToggle.MICROPHONE_MUTED, value=True),
            SetSetting(key="alert-enabled", value=False),
        ),
    ),
    Scene(
        id="relax",
        name="Relax",
        actions=(SetSetting(key="monitor-interval-seconds", value=5),),
        origin=SceneOrigin.USER,
    ),
]


def _service(
    toggles: _FakeToggles | None = None, audio: _FakeAudio | None = None
) -> tuple[SceneService, _FakeSettings, _FakeToggles, _FakeAudio]:
    settings = _FakeSettings()
    fake_toggles = toggles or _FakeToggles()
    fake_audio = audio or _FakeAudio()
    ports = ScenePorts(toggles=fake_toggles, settings=settings, audio=fake_audio)
    return SceneService(ports, scenes=_SCENES), settings, fake_toggles, fake_audio


def test_activate_writes_scene_settings() -> None:
    service, settings, _, _ = _service()

    service.activate("focus")

    assert settings.written["alert-enabled"] is False


def test_activate_applies_the_system_toggles() -> None:
    service, _, toggles, _ = _service()

    service.activate("focus")

    assert toggles.state == {
        SystemToggle.KEEP_AWAKE: True,
        SystemToggle.DO_NOT_DISTURB: True,
        SystemToggle.MICROPHONE_MUTED: True,
    }


def test_activate_records_the_active_scene() -> None:
    service, settings, _, _ = _service()

    service.activate("focus")

    assert service.active_id == "focus"
    assert settings.written["active-scene"] == "focus"


def test_activating_an_unknown_scene_does_nothing() -> None:
    service, settings, toggles, _ = _service()

    service.activate("ghost")

    assert service.active_id == ""
    assert settings.written == {}
    assert toggles.state == {}


def test_clear_turns_every_toggle_off_and_forgets_the_scene() -> None:
    service, settings, toggles, _ = _service()
    service.activate("focus")

    service.clear()

    assert all(value is False for value in toggles.state.values())
    assert service.active_id == ""
    assert settings.written["active-scene"] == ""


def test_changed_is_emitted_on_activate_and_clear() -> None:
    service, _, _, _ = _service()
    received: list[str] = []
    service.connect("changed", lambda _s: received.append(service.active_id))

    service.activate("relax")
    service.clear()

    assert received == ["relax", ""]


def test_scenes_property_exposes_the_known_scenes() -> None:
    service, _, _, _ = _service()

    assert [scene.id for scene in service.scenes] == ["focus", "relax"]


def test_find_returns_the_matching_scene() -> None:
    service, _, _, _ = _service()

    found = service.find("relax")

    assert found is not None and found.origin is SceneOrigin.USER


def test_find_returns_none_for_an_unknown_id() -> None:
    service, _, _, _ = _service()

    assert service.find("ghost") is None


# --- partial application --------------------------------------------------


def test_an_unavailable_toggle_is_skipped_and_the_rest_still_apply() -> None:
    toggles = _FakeToggles(supported={SystemToggle.KEEP_AWAKE})
    service, settings, _, _ = _service(toggles=toggles)

    service.activate("focus")

    assert settings.written["alert-enabled"] is False
    assert toggles.state == {SystemToggle.KEEP_AWAKE: True}


def test_the_last_outcomes_report_how_much_of_the_scene_applied() -> None:
    toggles = _FakeToggles(supported={SystemToggle.KEEP_AWAKE})
    service, _, _, _ = _service(toggles=toggles)

    service.activate("focus")

    statuses = [outcome.status for outcome in service.last_outcomes]
    assert statuses.count(Status.SKIPPED) == 2
    assert statuses.count(Status.APPLIED) == 2


def test_a_missing_output_device_is_skipped() -> None:
    scenes = [
        Scene(id="dock", name="Dock", actions=(SetOutputDevice(device="hdmi"),))
    ]
    settings = _FakeSettings()
    audio = _FakeAudio(available=set())
    service = SceneService(
        ScenePorts(toggles=_FakeToggles(), settings=settings, audio=audio), scenes=scenes
    )

    service.activate("dock")

    assert [outcome.status for outcome in service.last_outcomes] == [Status.SKIPPED]


def test_clearing_forgets_the_previous_outcomes() -> None:
    service, _, _, _ = _service()
    service.activate("focus")

    service.clear()

    assert service.last_outcomes == []


# --- replacing the scene list ---------------------------------------------


def test_set_scenes_replaces_the_known_scenes() -> None:
    service, _, _, _ = _service()

    service.set_scenes([Scene(id="new", name="New")])

    assert [scene.id for scene in service.scenes] == ["new"]


def test_set_scenes_clears_an_active_scene_that_no_longer_exists() -> None:
    service, _, _, _ = _service()
    service.activate("focus")

    service.set_scenes([Scene(id="other", name="Other")])

    assert service.active_id == ""


def test_set_scenes_keeps_an_active_scene_that_still_exists() -> None:
    service, _, _, _ = _service()
    service.activate("focus")

    service.set_scenes(_SCENES)

    assert service.active_id == "focus"
