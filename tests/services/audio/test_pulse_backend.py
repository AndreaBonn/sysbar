from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from pytest_mock import MockerFixture

from sysbar.services.audio.models import SinkInput
from sysbar.services.audio.pulse_backend import PulseAudioBackend


@dataclass
class FakeVolume:
    value_flat: float = 1.0


@dataclass
class FakeRawSinkInput:
    """Mimics a ``pulsectl`` sink-input object (attributes + proplist)."""

    index: int
    proplist: dict[str, Any] | None = field(default_factory=dict)
    volume: FakeVolume = field(default_factory=FakeVolume)
    mute: int = 0
    corked: int = 0


class FakePulse:
    def __init__(self, sink_inputs: list[FakeRawSinkInput]) -> None:
        self._sink_inputs = sink_inputs

    def sink_input_list(self) -> list[FakeRawSinkInput]:
        return list(self._sink_inputs)


def _backend(pulse: FakePulse | None = None) -> PulseAudioBackend:
    """Build a backend without triggering the ``pulsectl`` import in __init__."""
    backend = object.__new__(PulseAudioBackend)
    backend._pulse = pulse
    return backend


# --------------------------------------------------------------------------- #
# _to_sink_input — proplist field mapping
# --------------------------------------------------------------------------- #


def test_to_sink_input_maps_proplist_fields() -> None:
    raw = FakeRawSinkInput(
        index=7,
        proplist={
            "application.id": "org.app",
            "application.process.binary": "app",
            "application.name": "App",
            "application.process.id": "4242",
        },
        volume=FakeVolume(value_flat=0.5),
        mute=0,
        corked=0,
    )
    result = _backend()._to_sink_input(raw)
    assert result == SinkInput(
        index=7,
        app_id="org.app",
        binary="app",
        name="App",
        pid=4242,
        volume=0.5,
        muted=False,
        corked=False,
    )


def test_to_sink_input_valid_pid_parsed_to_int() -> None:
    raw = FakeRawSinkInput(index=1, proplist={"application.process.id": "99"})
    assert _backend()._to_sink_input(raw).pid == 99


def test_to_sink_input_missing_pid_is_none() -> None:
    raw = FakeRawSinkInput(index=1, proplist={})
    assert _backend()._to_sink_input(raw).pid is None


def test_to_sink_input_non_numeric_pid_is_none() -> None:
    raw = FakeRawSinkInput(index=1, proplist={"application.process.id": "abc"})
    assert _backend()._to_sink_input(raw).pid is None


def test_to_sink_input_none_proplist_defaults_to_empty() -> None:
    raw = FakeRawSinkInput(index=3, proplist=None)
    result = _backend()._to_sink_input(raw)
    assert result.app_id is None
    assert result.binary is None
    assert result.name is None
    assert result.pid is None


# --------------------------------------------------------------------------- #
# _to_sink_input — volume / mute / corked conversion
# --------------------------------------------------------------------------- #


def test_to_sink_input_volume_read_as_float() -> None:
    raw = FakeRawSinkInput(index=1, volume=FakeVolume(value_flat=0.75))
    result = _backend()._to_sink_input(raw)
    assert result.volume == 0.75
    assert isinstance(result.volume, float)


def test_to_sink_input_mute_and_corked_coerced_to_bool() -> None:
    raw = FakeRawSinkInput(index=1, mute=1, corked=1)
    result = _backend()._to_sink_input(raw)
    assert result.muted is True
    assert result.corked is True


def test_to_sink_input_unmuted_uncorked_coerced_to_false() -> None:
    raw = FakeRawSinkInput(index=1, mute=0, corked=0)
    result = _backend()._to_sink_input(raw)
    assert result.muted is False
    assert result.corked is False


# --------------------------------------------------------------------------- #
# list_sink_inputs
# --------------------------------------------------------------------------- #


def test_list_sink_inputs_maps_each_raw_entry() -> None:
    pulse = FakePulse(
        [
            FakeRawSinkInput(index=1, proplist={"application.id": "a"}),
            FakeRawSinkInput(index=2, proplist={"application.id": "b"}),
        ]
    )
    result = _backend(pulse).list_sink_inputs()
    assert [(si.index, si.app_id) for si in result] == [(1, "a"), (2, "b")]


def test_list_sink_inputs_empty_when_no_streams() -> None:
    assert _backend(FakePulse([])).list_sink_inputs() == []


# --------------------------------------------------------------------------- #
# subscribe — starts a single listener thread
# --------------------------------------------------------------------------- #


class PulseLoopStopError(Exception):
    """Stand-in for ``pulsectl.PulseLoopStop`` (the loop-break sentinel)."""


class FakePulsectl:
    PulseLoopStop = PulseLoopStopError


def _subscribable_backend() -> PulseAudioBackend:
    backend = object.__new__(PulseAudioBackend)
    backend._callback = None
    backend._listen_thread = None
    backend._running = False
    backend._pulsectl = FakePulsectl()
    return backend


def test_subscribe_starts_listener_thread_once(mocker: MockerFixture) -> None:
    thread = mocker.patch(
        "sysbar.services.audio.pulse_backend.threading.Thread", return_value=mocker.Mock()
    )
    backend = _subscribable_backend()

    backend.subscribe(lambda: None)
    backend.subscribe(lambda: None)

    thread.assert_called_once()
    thread.return_value.start.assert_called_once_with()
    assert backend._running is True


def test_subscribe_stores_callback(mocker: MockerFixture) -> None:
    mocker.patch("sysbar.services.audio.pulse_backend.threading.Thread")
    backend = _subscribable_backend()

    def cb() -> None:
        return None

    backend.subscribe(cb)

    assert backend._callback is cb


# --------------------------------------------------------------------------- #
# _on_pulse_event — invokes callback then stops the loop
# --------------------------------------------------------------------------- #


def test_on_pulse_event_invokes_callback_and_raises_stop() -> None:
    backend = _subscribable_backend()
    calls: list[str] = []
    backend._callback = lambda: calls.append("event")

    with pytest.raises(PulseLoopStopError):
        backend._on_pulse_event(object())

    assert calls == ["event"]


def test_on_pulse_event_raises_stop_without_callback() -> None:
    backend = _subscribable_backend()

    with pytest.raises(PulseLoopStopError):
        backend._on_pulse_event(object())
