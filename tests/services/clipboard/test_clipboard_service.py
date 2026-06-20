from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from sysbar.services.clipboard.models import ClipKind
from sysbar.services.clipboard.service import ClipboardService


def _ids() -> Callable[[], str]:
    counter = {"n": 0}

    def factory() -> str:
        value = f"id-{counter['n']}"
        counter["n"] += 1
        return value

    return factory


def _service(tmp_path: Path, max_entries: int = 50) -> ClipboardService:
    return ClipboardService(
        data_dir=tmp_path / "clipboard", max_entries=max_entries, id_factory=_ids()
    )


def test_capture_adds_entry_at_front(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.capture("first")
    service.capture("second")
    assert [e.text for e in service.items] == ["second", "first"]


def test_capture_ignores_blank_text(tmp_path: Path) -> None:
    service = _service(tmp_path)
    assert service.capture("   ") is None
    assert service.items == []


def test_capture_strips_and_labels(tmp_path: Path) -> None:
    entry = _service(tmp_path).capture("  hello world  ")
    assert entry is not None
    assert entry.text == "hello world"
    assert entry.kind is ClipKind.TEXT


def test_capture_classifies_url(tmp_path: Path) -> None:
    entry = _service(tmp_path).capture("https://example.com/path")
    assert entry is not None
    assert entry.kind is ClipKind.URL


def test_capture_truncates_long_label(tmp_path: Path) -> None:
    entry = _service(tmp_path).capture("x" * 200)
    assert entry is not None
    assert len(entry.label) <= 60


def test_capture_duplicate_moves_to_front_without_duplicating(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.capture("a")
    service.capture("b")
    service.capture("a")
    assert [e.text for e in service.items] == ["a", "b"]


def test_ring_buffer_evicts_oldest_unpinned(tmp_path: Path) -> None:
    service = _service(tmp_path, max_entries=2)
    service.capture("a")
    service.capture("b")
    service.capture("c")
    assert [e.text for e in service.items] == ["c", "b"]


def test_pinned_entry_is_not_evicted(tmp_path: Path) -> None:
    service = _service(tmp_path, max_entries=2)
    first = service.capture("keep")
    assert first is not None
    service.toggle_pin(first.id)
    service.capture("b")
    service.capture("c")
    texts = [e.text for e in service.items]
    assert "keep" in texts


def test_items_list_pinned_first(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.capture("plain")
    target = service.capture("important")
    assert target is not None
    service.capture("newest")
    service.toggle_pin(target.id)
    assert service.items[0].text == "important"


def test_remove_deletes_entry(tmp_path: Path) -> None:
    service = _service(tmp_path)
    entry = service.capture("gone")
    assert entry is not None
    service.remove(entry.id)
    assert service.items == []


def test_clear_removes_unpinned_keeps_pinned(tmp_path: Path) -> None:
    service = _service(tmp_path)
    pinned = service.capture("stay")
    assert pinned is not None
    service.toggle_pin(pinned.id)
    service.capture("drop")
    service.clear()
    assert [e.text for e in service.items] == ["stay"]


def test_search_filters_case_insensitive(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.capture("Hello World")
    service.capture("goodbye")
    results = service.search("hello")
    assert [e.text for e in results] == ["Hello World"]


def test_search_blank_returns_all(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.capture("a")
    service.capture("b")
    assert len(service.search("  ")) == 2


def test_persistence_roundtrip(tmp_path: Path) -> None:
    service = _service(tmp_path)
    entry = service.capture("persisted")
    assert entry is not None
    service.toggle_pin(entry.id)

    reloaded = ClipboardService(data_dir=tmp_path / "clipboard", id_factory=_ids())
    reloaded.load()
    assert [(e.text, e.pinned) for e in reloaded.items] == [("persisted", True)]


def test_load_without_manifest_is_noop(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.load()
    assert service.items == []


def test_load_with_corrupt_manifest_recovers_empty(tmp_path: Path) -> None:
    data_dir = tmp_path / "clipboard"
    data_dir.mkdir(parents=True)
    (data_dir / "manifest.json").write_text("{not json", encoding="utf-8")
    service = ClipboardService(data_dir=data_dir, id_factory=_ids())
    service.load()
    assert service.items == []


def test_evict_noop_when_pinned_entries_exceed_cap(tmp_path: Path) -> None:
    # A manifest can hold more pinned entries than the current cap; eviction must
    # then stop instead of dropping a pinned entry or crashing.
    data_dir = tmp_path / "clipboard"
    data_dir.mkdir(parents=True)
    (data_dir / "manifest.json").write_text(
        json.dumps(
            [
                {"id": "1", "kind": "text", "text": "a", "label": "a", "pinned": True},
                {"id": "2", "kind": "text", "text": "b", "label": "b", "pinned": True},
            ]
        ),
        encoding="utf-8",
    )
    service = ClipboardService(data_dir=data_dir, max_entries=1, id_factory=_ids())
    service.load()
    service.capture("c")
    assert {e.text for e in service.items} == {"a", "b"}


def test_items_changed_emitted_on_capture(tmp_path: Path) -> None:
    service = _service(tmp_path)
    received: list[bool] = []
    service.connect("items-changed", lambda _src: received.append(True))
    service.capture("x")
    assert received == [True]
