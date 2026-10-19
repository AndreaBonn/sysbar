"""Pending shelf clears preserve staged files until undo or commit."""

from __future__ import annotations

from pathlib import Path

from sysbar.services.shelf.pending_clear import PendingClear
from sysbar.services.shelf.shelf_service import ShelfService


def test_clear_empty_shelf_returns_no_batch(tmp_path: Path) -> None:
    service = ShelfService(data_dir=tmp_path / "shelf")
    assert PendingClear(service=service).clear() is None
    assert service.items == []


def test_clear_then_undo_restores_original_order_and_staging(tmp_path: Path) -> None:
    service = ShelfService(data_dir=tmp_path / "shelf")
    first = service.add_image(data=b"first")
    second = service.add_image(data=b"second")
    pending = PendingClear(service=service)

    assert pending.clear() == 1
    assert service.items == []
    third = service.add_image(data=b"third")
    pending.undo()

    assert service.items == [first, second, third]
    assert [Path(item.path or "").read_bytes() for item in service.items] == [
        b"first",
        b"second",
        b"third",
    ]


def test_second_clear_discards_first_batch_from_disk(tmp_path: Path) -> None:
    service = ShelfService(data_dir=tmp_path / "shelf")
    first = service.add_image(data=b"first")
    staged = Path(first.path or "")
    assert staged.read_bytes() == b"first"
    pending = PendingClear(service=service)
    assert pending.clear() == 1
    second = service.add_image(data=b"second")

    assert pending.clear() == 2

    assert not staged.exists()
    assert Path(second.path or "").read_bytes() == b"second"
    pending.undo()
    assert service.items == [second]


def test_commit_then_undo_keeps_shelf_empty_and_staging_removed(tmp_path: Path) -> None:
    service = ShelfService(data_dir=tmp_path / "shelf")
    image = service.add_image(data=b"image")
    staged = Path(image.path or "")
    assert staged.read_bytes() == b"image"
    pending = PendingClear(service=service)
    assert pending.clear() == 1

    pending.commit()
    pending.undo()

    assert service.items == []
    assert not staged.exists()
    pending.commit()


def test_undo_without_clear_preserves_items(tmp_path: Path) -> None:
    service = ShelfService(data_dir=tmp_path / "shelf")
    image = service.add_image(data=b"image")

    PendingClear(service=service).undo()

    assert service.items == [image]
    assert Path(image.path or "").read_bytes() == b"image"


def test_commit_of_a_superseded_batch_keeps_the_current_one(tmp_path: Path) -> None:
    """The first toast timing out must not delete what a later clear detached."""
    service = ShelfService(data_dir=tmp_path / "shelf")
    service.add_image(data=b"first")
    pending = PendingClear(service=service)
    first_batch = pending.clear()
    second = service.add_image(data=b"second")
    pending.clear()

    pending.commit(batch=first_batch)
    pending.undo()

    assert service.items == [second]
    assert Path(second.path or "").read_bytes() == b"second"


def test_undo_of_a_superseded_batch_restores_nothing(tmp_path: Path) -> None:
    """The first toast's Undo cannot bring back the second clear's items."""
    service = ShelfService(data_dir=tmp_path / "shelf")
    service.add_image(data=b"first")
    pending = PendingClear(service=service)
    first_batch = pending.clear()
    second = service.add_image(data=b"second")
    second_batch = pending.clear()

    pending.undo(batch=first_batch)
    assert service.items == []

    pending.undo(batch=second_batch)
    assert service.items == [second]
