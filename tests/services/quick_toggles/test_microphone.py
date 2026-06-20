from __future__ import annotations

from sysbar.services.quick_toggles.microphone import MicrophoneToggle


class FakeMicBackend:
    def __init__(self, muted: bool | None = False, in_use: bool = False) -> None:
        self._muted = muted
        self._in_use = in_use
        self.set_calls: list[bool] = []

    def is_muted(self) -> bool | None:
        return self._muted

    def set_muted(self, muted: bool) -> None:
        self.set_calls.append(muted)
        self._muted = muted

    def is_in_use(self) -> bool:
        return self._in_use


def test_is_muted_reflects_backend() -> None:
    assert MicrophoneToggle(FakeMicBackend(muted=True)).is_muted() is True
    assert MicrophoneToggle(FakeMicBackend(muted=False)).is_muted() is False


def test_is_muted_false_when_no_default_source() -> None:
    assert MicrophoneToggle(FakeMicBackend(muted=None)).is_muted() is False


def test_toggle_mutes_an_unmuted_source() -> None:
    backend = FakeMicBackend(muted=False)
    MicrophoneToggle(backend).toggle()
    assert backend.set_calls == [True]


def test_toggle_unmutes_a_muted_source() -> None:
    backend = FakeMicBackend(muted=True)
    MicrophoneToggle(backend).toggle()
    assert backend.set_calls == [False]


def test_toggle_noop_when_no_default_source() -> None:
    backend = FakeMicBackend(muted=None)
    MicrophoneToggle(backend).toggle()
    assert backend.set_calls == []


def test_is_in_use_reflects_backend() -> None:
    assert MicrophoneToggle(FakeMicBackend(in_use=True)).is_in_use() is True
    assert MicrophoneToggle(FakeMicBackend(in_use=False)).is_in_use() is False
