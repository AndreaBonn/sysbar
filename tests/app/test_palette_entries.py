"""Which sources the palette draws from, and that each one arrives."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

import pytest

from sysbar.app.commands.actions import CommandHandlers
from sysbar.app.commands.catalogue import CATALOGUE
from sysbar.app.palette_entries import collect
from sysbar.app.tray.menu_builder import QuickToggleState
from sysbar.services.audio.models import AudioDevice
from sysbar.services.clipboard.models import ClipEntry, ClipKind
from sysbar.services.palette.models import EntryKind
from sysbar.services.scenes.models import Scene
from sysbar.services.shelf.models import ItemKind, ShelfItem


def _handlers(record: list[str]) -> CommandHandlers:
    def simple(name: str) -> Callable[[], None]:
        return lambda: record.append(name)

    def parametric(name: str) -> Callable[[str], None]:
        return lambda value: record.append(f"{name}:{value}")

    return CommandHandlers(
        simple={
            command.id: simple(command.id.value)
            for command in CATALOGUE
            if not command.is_parametric
        },
        parametric={
            command.id: parametric(command.id.value)
            for command in CATALOGUE
            if command.is_parametric
        },
    )


@dataclass
class _FakeClipboard:
    clips: list[ClipEntry] = field(default_factory=list)
    copied: list[str] = field(default_factory=list)
    is_enabled: bool = True

    def entries(self) -> list[ClipEntry]:
        return self.clips

    def copy(self, text: str) -> None:
        self.copied.append(text)


@dataclass
class _FakeShelf:
    shelf_items: list[ShelfItem] = field(default_factory=list)
    opened: list[str] = field(default_factory=list)
    is_enabled: bool = True

    def items(self) -> list[ShelfItem]:
        return self.shelf_items

    def open_uri(self, uri: str) -> None:
        self.opened.append(uri)


@dataclass
class _FakeScenes:
    scenes: list[Scene] = field(default_factory=list)
    active_id: str = ""
    activated: list[str] = field(default_factory=list)

    def activate(self, scene_id: str) -> None:
        self.activated.append(scene_id)


@dataclass
class _FakeAudio:
    sinks: list[AudioDevice] = field(default_factory=list)
    sources: list[AudioDevice] = field(default_factory=list)
    selected: list[str] = field(default_factory=list)

    def outputs(self) -> list[AudioDevice]:
        return self.sinks

    def inputs(self) -> list[AudioDevice]:
        return self.sources

    def set_output(self, name: str) -> None:
        self.selected.append(f"out:{name}")

    def set_input(self, name: str) -> None:
        self.selected.append(f"in:{name}")


@dataclass
class _FakeToggles:
    toggle_state: QuickToggleState = field(default_factory=QuickToggleState)

    def state(self) -> QuickToggleState:
        return self.toggle_state


@dataclass
class _FakeFeatures:
    clipboard: _FakeClipboard
    shelf: _FakeShelf
    scenes: _FakeScenes
    audio: _FakeAudio
    toggles: _FakeToggles


def _features(**overrides: Any) -> Any:
    base = _FakeFeatures(
        clipboard=_FakeClipboard(),
        shelf=_FakeShelf(),
        scenes=_FakeScenes(),
        audio=_FakeAudio(),
        toggles=_FakeToggles(),
    )
    for name, value in overrides.items():
        setattr(base, name, value)
    return base


def _scene(scene_id: str, name: str) -> Scene:
    return Scene(
        id=scene_id, name=name, keep_awake=False, do_not_disturb=False, mute_microphone=False
    )


def _device(name: str, description: str, kind: str = "sink") -> AudioDevice:
    return AudioDevice(index=1, name=name, description=description, kind=kind, is_default=False)


@pytest.fixture
def record() -> list[str]:
    return []


def _kinds(entries: list[Any]) -> set[EntryKind]:
    return {entry.kind for entry in entries}


def test_commands_are_always_present(record: list[str]) -> None:
    entries = collect(cast(Any, _features()), _handlers(record))

    assert EntryKind.COMMAND in _kinds(entries)


def test_an_empty_session_still_lists_the_commands(record: list[str]) -> None:
    entries = collect(cast(Any, _features()), _handlers(record))

    assert _kinds(entries) == {EntryKind.COMMAND}


def test_scenes_are_collected(record: list[str]) -> None:
    features = _features(scenes=_FakeScenes(scenes=[_scene("focus", "Focus")]))

    entries = collect(cast(Any, features), _handlers(record))

    assert EntryKind.SCENE in _kinds(entries)


def test_a_scene_row_activates_through_the_feature(record: list[str]) -> None:
    fake = _FakeScenes(scenes=[_scene("focus", "Focus")])

    entries = collect(cast(Any, _features(scenes=fake)), _handlers(record))
    next(e for e in entries if e.kind is EntryKind.SCENE).activate()

    assert fake.activated == ["focus"]


def test_clipboard_entries_are_collected(record: list[str]) -> None:
    clip = ClipEntry(id="1", kind=ClipKind.TEXT, text="hello", label="hello")
    features = _features(clipboard=_FakeClipboard(clips=[clip]))

    entries = collect(cast(Any, features), _handlers(record))

    assert EntryKind.CLIPBOARD in _kinds(entries)


def test_a_clipboard_row_copies_through_the_feature(record: list[str]) -> None:
    clip = ClipEntry(id="1", kind=ClipKind.TEXT, text="hello", label="hello")
    fake = _FakeClipboard(clips=[clip])

    entries = collect(cast(Any, _features(clipboard=fake)), _handlers(record))
    next(e for e in entries if e.kind is EntryKind.CLIPBOARD).activate()

    assert fake.copied == ["hello"]


def test_shelf_items_are_collected(record: list[str]) -> None:
    item = ShelfItem(id="1", kind=ItemKind.URL, label="link", text="https://example.com")
    features = _features(shelf=_FakeShelf(shelf_items=[item]))

    entries = collect(cast(Any, features), _handlers(record))

    assert EntryKind.SHELF in _kinds(entries)


def test_a_shelf_row_opens_through_the_feature(record: list[str]) -> None:
    item = ShelfItem(id="1", kind=ItemKind.URL, label="link", text="https://example.com")
    fake = _FakeShelf(shelf_items=[item])

    entries = collect(cast(Any, _features(shelf=fake)), _handlers(record))
    next(e for e in entries if e.kind is EntryKind.SHELF).activate()

    assert fake.opened == ["https://example.com"]


def test_both_output_and_input_devices_are_collected(record: list[str]) -> None:
    audio = _FakeAudio(
        sinks=[_device("sink1", "Speakers")],
        sources=[_device("src1", "Microphone", kind="source")],
    )

    entries = collect(cast(Any, _features(audio=audio)), _handlers(record))
    devices = [entry for entry in entries if entry.kind is EntryKind.DEVICE]

    assert len(devices) == 2


def test_output_and_input_rows_carry_different_subtitles(record: list[str]) -> None:
    audio = _FakeAudio(
        sinks=[_device("sink1", "Speakers")],
        sources=[_device("src1", "Microphone", kind="source")],
    )

    entries = collect(cast(Any, _features(audio=audio)), _handlers(record))
    subtitles = {entry.subtitle for entry in entries if entry.kind is EntryKind.DEVICE}

    assert len(subtitles) == 2


def test_selecting_an_output_goes_to_the_output_setter(record: list[str]) -> None:
    audio = _FakeAudio(sinks=[_device("sink1", "Speakers")])

    entries = collect(cast(Any, _features(audio=audio)), _handlers(record))
    next(e for e in entries if e.kind is EntryKind.DEVICE).activate()

    assert audio.selected == ["out:sink1"]


def test_every_entry_id_is_unique(record: list[str]) -> None:
    """Ids namespace their source, so a scene and a command cannot collide."""
    features = _features(
        scenes=_FakeScenes(scenes=[_scene("focus", "Focus")]),
        clipboard=_FakeClipboard(
            clips=[ClipEntry(id="1", kind=ClipKind.TEXT, text="a", label="a")]
        ),
        shelf=_FakeShelf(
            shelf_items=[ShelfItem(id="1", kind=ItemKind.URL, label="l", text="https://x.dev")]
        ),
    )

    entries = collect(cast(Any, features), _handlers(record))
    ids = [entry.id for entry in entries]

    assert len(ids) == len(set(ids))


def test_a_disabled_clipboard_contributes_nothing(record: list[str]) -> None:
    features = _features(clipboard=_FakeClipboard(clips=[], is_enabled=False))

    entries = collect(cast(Any, features), _handlers(record))

    assert EntryKind.CLIPBOARD not in _kinds(entries)
