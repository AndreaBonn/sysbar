"""How session data becomes palette rows."""

from __future__ import annotations

import pytest

from sysbar.services.audio.models import AudioDevice
from sysbar.services.clipboard.models import ClipEntry, ClipKind
from sysbar.services.palette.models import EntryKind
from sysbar.services.palette.sources import (
    clipboard_entries,
    device_entries,
    scene_entries,
    shelf_entries,
)
from sysbar.services.scenes.models import Scene
from sysbar.services.shelf.models import ItemKind, ShelfItem


@pytest.fixture
def calls() -> list[str]:
    return []


# --- clipboard ------------------------------------------------------------


def _clip(text: str, *, label: str = "", pinned: bool = False) -> ClipEntry:
    return ClipEntry(id="1", kind=ClipKind.TEXT, text=text, label=label or text, pinned=pinned)


def test_a_clipboard_row_copies_the_original_text(calls: list[str]) -> None:
    entries = clipboard_entries([_clip("hello there")], calls.append)

    entries[0].activate()

    assert calls == ["hello there"]


def test_an_ordinary_clipboard_row_shows_its_label(calls: list[str]) -> None:
    entries = clipboard_entries([_clip("hello there")], calls.append)

    assert entries[0].title == "hello there"
    assert entries[0].masked is False


def test_a_credential_row_is_masked(calls: list[str]) -> None:
    entries = clipboard_entries([_clip("ghp_16CharactersAndThenSomeMore1234")], calls.append)

    assert entries[0].masked is True
    assert "16CharactersAndThenSomeMore1234" not in entries[0].title


def test_a_masked_row_is_still_searchable_by_its_content(calls: list[str]) -> None:
    entries = clipboard_entries([_clip("ghp_16CharactersAndThenSomeMore1234")], calls.append)

    assert entries[0].haystack == "ghp_16CharactersAndThenSomeMore1234"


def test_a_masked_row_still_copies_the_real_value(calls: list[str]) -> None:
    secret = "ghp_16CharactersAndThenSomeMore1234"
    entries = clipboard_entries([_clip(secret)], calls.append)

    entries[0].activate()

    assert calls == [secret]


def test_a_pinned_clipboard_row_outweighs_an_unpinned_one(calls: list[str]) -> None:
    entries = clipboard_entries([_clip("plain"), _clip("important", pinned=True)], calls.append)

    assert entries[1].weight > entries[0].weight


def test_clipboard_rows_are_tagged_as_clipboard(calls: list[str]) -> None:
    entries = clipboard_entries([_clip("x")], calls.append)

    assert entries[0].kind is EntryKind.CLIPBOARD


def test_no_clips_produce_no_rows(calls: list[str]) -> None:
    assert clipboard_entries([], calls.append) == []


# --- shelf ----------------------------------------------------------------


def test_a_shelf_url_row_opens_its_target(calls: list[str]) -> None:
    item = ShelfItem(id="1", kind=ItemKind.URL, label="Sysbar", text="https://example.com")

    entries = shelf_entries([item], calls.append)
    entries[0].activate()

    assert calls == ["https://example.com"]


def test_a_shelf_row_with_nothing_to_open_is_unavailable(calls: list[str]) -> None:
    item = ShelfItem(id="1", kind=ItemKind.TEXT, label="a note", text="just text")

    entries = shelf_entries([item], calls.append)

    assert entries[0].is_runnable is False
    assert entries[0].unavailable_reason


def test_an_unavailable_shelf_row_does_nothing_when_activated(calls: list[str]) -> None:
    item = ShelfItem(id="1", kind=ItemKind.TEXT, label="a note", text="just text")

    shelf_entries([item], calls.append)[0].activate()

    assert calls == []


def test_a_relative_file_path_is_not_openable(calls: list[str]) -> None:
    item = ShelfItem(id="1", kind=ItemKind.FILE, label="notes", path="relative/notes.txt")

    assert shelf_entries([item], calls.append)[0].is_runnable is False


# --- scenes ---------------------------------------------------------------


def _scene(scene_id: str, name: str) -> Scene:
    return Scene(
        id=scene_id, name=name, keep_awake=False, do_not_disturb=False, mute_microphone=False
    )


def test_a_scene_row_activates_its_own_scene(calls: list[str]) -> None:
    scenes = [_scene("focus", "Focus"), _scene("presentation", "Presentation")]

    entries = scene_entries(scenes, "", calls.append, lambda scene: scene.name)
    entries[1].activate()

    assert calls == ["presentation"]


def test_the_active_scene_outweighs_the_others(calls: list[str]) -> None:
    scenes = [_scene("focus", "Focus"), _scene("presentation", "Presentation")]

    entries = scene_entries(scenes, "presentation", calls.append, lambda scene: scene.name)

    assert entries[1].weight > entries[0].weight


def test_the_active_scene_says_so(calls: list[str]) -> None:
    entries = scene_entries([_scene("focus", "Focus")], "focus", calls.append, lambda s: s.name)

    assert entries[0].subtitle == "Active scene"


def test_scene_titles_come_from_the_display_name_function(calls: list[str]) -> None:
    entries = scene_entries(
        [_scene("focus", "Focus")], "", calls.append, lambda scene: f"tradotto:{scene.name}"
    )

    assert entries[0].title == "tradotto:Focus"


# --- devices --------------------------------------------------------------


def _device(name: str, description: str, *, default: bool = False) -> AudioDevice:
    return AudioDevice(index=1, name=name, description=description, kind="sink", is_default=default)


def test_a_device_row_selects_its_device(calls: list[str]) -> None:
    devices = [_device("alsa.hdmi", "HDMI Output"), _device("alsa.speaker", "Speakers")]

    entries = device_entries(devices, calls.append, "Set as output")
    entries[0].activate()

    assert calls == ["alsa.hdmi"]


def test_the_current_default_device_is_not_actionable(calls: list[str]) -> None:
    entries = device_entries([_device("a", "Speakers", default=True)], calls.append, "Output")

    assert entries[0].is_runnable is False
    assert entries[0].unavailable_reason == "Already the default device"


def test_a_device_falls_back_to_its_name_without_a_description(calls: list[str]) -> None:
    entries = device_entries([_device("alsa.hdmi", "")], calls.append, "Output")

    assert entries[0].title == "alsa.hdmi"


def test_device_rows_carry_the_given_subtitle(calls: list[str]) -> None:
    entries = device_entries([_device("a", "Mic")], calls.append, "Set as input")

    assert entries[0].subtitle == "Set as input"


def test_output_and_input_rows_do_not_collide_by_id(calls: list[str]) -> None:
    sink = AudioDevice(index=1, name="same", description="d", kind="sink", is_default=False)
    source = AudioDevice(index=1, name="same", description="d", kind="source", is_default=False)

    ids = {
        device_entries([sink], calls.append, "out")[0].id,
        device_entries([source], calls.append, "in")[0].id,
    }

    assert len(ids) == 2
