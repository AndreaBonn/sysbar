from __future__ import annotations

from sysbar.services.audio.device_switcher import DeviceSwitcher
from sysbar.services.audio.models import AudioDevice, SinkInput


def _sink(index: int, name: str, default: bool = False) -> AudioDevice:
    return AudioDevice(
        index=index, name=name, description=name.title(), kind="sink", is_default=default
    )


def _source(index: int, name: str, default: bool = False) -> AudioDevice:
    return AudioDevice(
        index=index, name=name, description=name.title(), kind="source", is_default=default
    )


class FakeDeviceBackend:
    def __init__(
        self,
        sinks: list[AudioDevice],
        sources: list[AudioDevice],
        sink_inputs: list[SinkInput],
    ) -> None:
        self.sinks = sinks
        self.sources = sources
        self.sink_inputs = sink_inputs
        self.default_sink: str | None = None
        self.default_source: str | None = None
        self.moves: list[tuple[int, int]] = []

    def list_sinks(self) -> list[AudioDevice]:
        return self.sinks

    def list_sources(self) -> list[AudioDevice]:
        return self.sources

    def list_sink_inputs(self) -> list[SinkInput]:
        return self.sink_inputs

    def set_default_sink(self, name: str) -> None:
        self.default_sink = name

    def set_default_source(self, name: str) -> None:
        self.default_source = name

    def move_sink_input(self, input_index: int, sink_index: int) -> None:
        self.moves.append((input_index, sink_index))


def test_refresh_exposes_outputs_and_inputs() -> None:
    backend = FakeDeviceBackend([_sink(0, "hdmi")], [_source(1, "mic")], [])
    switcher = DeviceSwitcher(backend)

    switcher.refresh()

    assert [d.name for d in switcher.outputs] == ["hdmi"]
    assert [d.name for d in switcher.inputs] == ["mic"]


def test_refresh_emits_devices_changed() -> None:
    backend = FakeDeviceBackend([], [], [])
    switcher = DeviceSwitcher(backend)
    received: list[bool] = []
    switcher.connect("devices-changed", lambda _src: received.append(True))

    switcher.refresh()

    assert received == [True]


def test_set_default_output_sets_default_and_moves_all_streams() -> None:
    sinks = [_sink(0, "speakers", default=True), _sink(7, "headphones")]
    inputs = [SinkInput(index=11), SinkInput(index=12)]
    backend = FakeDeviceBackend(sinks, [], inputs)
    switcher = DeviceSwitcher(backend)
    switcher.refresh()

    switcher.set_default_output("headphones")

    assert backend.default_sink == "headphones"
    assert backend.moves == [(11, 7), (12, 7)]


def test_set_default_output_ignores_unknown_device() -> None:
    backend = FakeDeviceBackend([_sink(0, "speakers")], [], [SinkInput(index=1)])
    switcher = DeviceSwitcher(backend)
    switcher.refresh()

    switcher.set_default_output("ghost")

    assert backend.default_sink is None
    assert backend.moves == []


def test_set_default_input_sets_default_source() -> None:
    backend = FakeDeviceBackend([], [_source(3, "webcam"), _source(4, "headset")], [])
    switcher = DeviceSwitcher(backend)
    switcher.refresh()

    switcher.set_default_input("headset")

    assert backend.default_source == "headset"


def test_set_default_input_ignores_unknown_device() -> None:
    backend = FakeDeviceBackend([], [_source(3, "webcam")], [])
    switcher = DeviceSwitcher(backend)
    switcher.refresh()

    switcher.set_default_input("ghost")

    assert backend.default_source is None
