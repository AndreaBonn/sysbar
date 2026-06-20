from __future__ import annotations

from collections.abc import Callable

from sysbar.core.constants import KEEP_AWAKE_SHORTCUT_ID
from sysbar.services.hotkey.manager import HotkeyManager


class FakeShortcuts:
    def __init__(self) -> None:
        self.bound: list[tuple[str, str]] = []
        self._callbacks: dict[str, Callable[[], None]] = {}

    def bind(self, shortcut_id: str, description: str, on_activated: Callable[[], None]) -> None:
        self.bound.append((shortcut_id, description))
        self._callbacks[shortcut_id] = on_activated

    def activate(self, shortcut_id: str) -> None:
        self._callbacks[shortcut_id]()


def test_start_binds_keep_awake_shortcut_when_enabled() -> None:
    shortcuts = FakeShortcuts()
    HotkeyManager(shortcuts, on_trigger=lambda: None, enabled=lambda: True).start()
    assert [sid for sid, _ in shortcuts.bound] == [KEEP_AWAKE_SHORTCUT_ID]


def test_start_does_not_bind_when_disabled() -> None:
    shortcuts = FakeShortcuts()
    HotkeyManager(shortcuts, on_trigger=lambda: None, enabled=lambda: False).start()
    assert shortcuts.bound == []


def test_activation_invokes_trigger() -> None:
    shortcuts = FakeShortcuts()
    calls: list[str] = []
    HotkeyManager(
        shortcuts, on_trigger=lambda: calls.append("toggled"), enabled=lambda: True
    ).start()
    shortcuts.activate(KEEP_AWAKE_SHORTCUT_ID)
    assert calls == ["toggled"]
