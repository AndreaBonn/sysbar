"""Behaviour of the lazy window slot."""

from __future__ import annotations

from collections.abc import Callable

from sysbar.app.windows import WindowSlot


class _FakeWindow:
    """Records presents and lets a test fire the ``close-request`` signal."""

    def __init__(self, label: str = "window") -> None:
        self.label = label
        self.present_count = 0
        self._handlers: dict[str, Callable[..., bool]] = {}

    def present(self) -> None:
        self.present_count += 1

    def connect(self, detailed_signal: str, handler: Callable[..., bool]) -> int:
        self._handlers[detailed_signal] = handler
        return 1

    def emit_close(self) -> bool:
        return self._handlers["close-request"](self)


class _CountingFactory:
    def __init__(self) -> None:
        self.calls = 0
        self.built: list[_FakeWindow] = []

    def __call__(self) -> _FakeWindow:
        self.calls += 1
        window = _FakeWindow(label=f"window-{self.calls}")
        self.built.append(window)
        return window


def test_slot_starts_closed() -> None:
    assert WindowSlot(_CountingFactory()).is_open is False


def test_present_builds_the_window_once_and_reuses_it() -> None:
    factory = _CountingFactory()
    slot = WindowSlot(factory)

    first = slot.present()
    second = slot.present()

    assert factory.calls == 1
    assert first is second
    assert first.present_count == 2
    assert slot.is_open is True


def test_close_request_drops_the_reference_so_the_next_present_rebuilds() -> None:
    factory = _CountingFactory()
    slot = WindowSlot(factory)
    original = slot.present()

    original.emit_close()

    assert slot.is_open is False
    rebuilt = slot.present()
    assert factory.calls == 2
    assert rebuilt is not original


def test_close_request_lets_the_default_close_proceed() -> None:
    slot: WindowSlot[_FakeWindow] = WindowSlot(_CountingFactory())
    window = slot.present()

    assert window.emit_close() is False


def test_close_request_notifies_the_callback_once() -> None:
    closed: list[str] = []
    slot = WindowSlot(_CountingFactory(), on_closed=lambda: closed.append("closed"))
    window = slot.present()

    window.emit_close()

    assert closed == ["closed"]


def test_close_callback_is_optional() -> None:
    slot: WindowSlot[_FakeWindow] = WindowSlot(_CountingFactory())
    window = slot.present()

    assert window.emit_close() is False


def test_if_open_runs_the_action_on_the_live_window() -> None:
    slot = WindowSlot(_CountingFactory())
    slot.present()
    seen: list[str] = []

    slot.if_open(lambda window: seen.append(window.label))

    assert seen == ["window-1"]


def test_if_open_does_nothing_when_closed() -> None:
    slot = WindowSlot(_CountingFactory())
    seen: list[str] = []

    slot.if_open(lambda window: seen.append(window.label))

    assert seen == []


def test_if_open_does_nothing_after_the_window_closes() -> None:
    slot = WindowSlot(_CountingFactory())
    window = slot.present()
    window.emit_close()
    seen: list[str] = []

    slot.if_open(lambda live: seen.append(live.label))

    assert seen == []


def test_forget_drops_the_reference_without_invoking_the_callback() -> None:
    closed: list[str] = []
    factory = _CountingFactory()
    slot = WindowSlot(factory, on_closed=lambda: closed.append("closed"))
    slot.present()

    slot.forget()

    assert slot.is_open is False
    assert closed == []
    slot.present()
    assert factory.calls == 2
