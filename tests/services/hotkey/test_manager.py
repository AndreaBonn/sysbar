from __future__ import annotations

from collections.abc import Callable

from sysbar.services.hotkey.manager import HotkeyBinding, HotkeyManager


class FakeShortcuts:
    def __init__(self) -> None:
        self.bound: list[tuple[str, str]] = []
        self._callbacks: dict[str, Callable[[], None]] = {}

    def bind(self, shortcut_id: str, description: str, on_activated: Callable[[], None]) -> None:
        self.bound.append((shortcut_id, description))
        self._callbacks[shortcut_id] = on_activated

    def activate(self, shortcut_id: str) -> None:
        self._callbacks[shortcut_id]()


def _binding(shortcut_id: str, trigger: Callable[[], None], *, enabled: bool) -> HotkeyBinding:
    return HotkeyBinding(
        shortcut_id=shortcut_id,
        description=shortcut_id.replace("-", " ").title(),
        trigger=trigger,
        enabled=lambda: enabled,
    )


def test_start_binds_only_enabled_shortcuts() -> None:
    shortcuts = FakeShortcuts()
    bindings = [
        _binding("toggle-keep-awake", lambda: None, enabled=True),
        _binding("open-shelf", lambda: None, enabled=False),
        _binding("open-clipboard", lambda: None, enabled=True),
    ]
    HotkeyManager(shortcuts, bindings).start()
    assert [sid for sid, _ in shortcuts.bound] == ["toggle-keep-awake", "open-clipboard"]


def test_start_with_no_bindings_binds_nothing() -> None:
    shortcuts = FakeShortcuts()
    HotkeyManager(shortcuts, []).start()
    assert shortcuts.bound == []


def test_start_survives_a_binding_that_raises() -> None:
    # A backend without the GlobalShortcuts portal raises on bind; that must not
    # crash startup, and later bindings must still be attempted.
    class RaisingShortcuts(FakeShortcuts):
        def bind(
            self, shortcut_id: str, description: str, on_activated: Callable[[], None]
        ) -> None:
            if shortcut_id == "open-shelf":
                raise RuntimeError("GlobalShortcuts portal not available")
            super().bind(shortcut_id, description, on_activated)

    shortcuts = RaisingShortcuts()
    bindings = [
        _binding("open-shelf", lambda: None, enabled=True),
        _binding("open-clipboard", lambda: None, enabled=True),
    ]

    HotkeyManager(shortcuts, bindings).start()  # must not raise

    assert [sid for sid, _ in shortcuts.bound] == ["open-clipboard"]


def test_activation_invokes_matching_trigger() -> None:
    shortcuts = FakeShortcuts()
    calls: list[str] = []
    bindings = [
        _binding("toggle-keep-awake", lambda: calls.append("awake"), enabled=True),
        _binding("open-shelf", lambda: calls.append("shelf"), enabled=True),
    ]
    HotkeyManager(shortcuts, bindings).start()

    shortcuts.activate("open-shelf")

    assert calls == ["shelf"]
