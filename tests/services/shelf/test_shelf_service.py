import json
from collections.abc import Callable
from pathlib import Path

from sysbar.services.shelf.models import ItemKind, ShelfItem
from sysbar.services.shelf.shelf_service import ShelfService


def _ids() -> Callable[[], str]:
    counter = {"n": 0}

    def factory() -> str:
        value = f"id-{counter['n']}"
        counter["n"] += 1
        return value

    return factory


def _service(tmp_path: Path) -> ShelfService:
    return ShelfService(data_dir=tmp_path / "shelf", id_factory=_ids())


def test_add_file_keeps_reference_and_label(tmp_path: Path) -> None:
    service = _service(tmp_path)
    item = service.add_file("/home/user/report.pdf")
    assert item.kind is ItemKind.FILE
    assert item.label == "report.pdf"
    assert item.path == "/home/user/report.pdf"


def test_add_url_stores_text(tmp_path: Path) -> None:
    item = _service(tmp_path).add_url("https://example.com")
    assert item.kind is ItemKind.URL
    assert item.text == "https://example.com"


def test_add_text_truncates_label(tmp_path: Path) -> None:
    item = _service(tmp_path).add_text("a" * 100)
    assert item.kind is ItemKind.TEXT
    assert len(item.label) == 40
    assert item.text == "a" * 100


def test_add_image_stages_file(tmp_path: Path) -> None:
    service = _service(tmp_path)
    item = service.add_image(b"\x89PNG-data", suffix=".png")
    assert item.kind is ItemKind.IMAGE
    assert item.path is not None
    staged = Path(item.path)
    assert staged.exists()
    assert staged.read_bytes() == b"\x89PNG-data"


def test_remove_deletes_item_and_staged_file(tmp_path: Path) -> None:
    service = _service(tmp_path)
    item = service.add_image(b"data", suffix=".png")
    staged = Path(item.path or "")
    service.remove(item.id)
    assert service.items == []
    assert not staged.exists()


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.add_file("/tmp/a.txt")
    service.add_url("https://example.com")

    reloaded = ShelfService(data_dir=tmp_path / "shelf", id_factory=_ids())
    reloaded.load()
    assert [item.label for item in reloaded.items] == ["a.txt", "https://example.com"]


def test_clear_empties_shelf(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.add_file("/tmp/a.txt")
    service.clear()
    assert service.items == []


def test_remove_unknown_id_is_noop(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.add_file("/tmp/a.txt")
    service.remove("does-not-exist")
    assert [item.label for item in service.items] == ["a.txt"]


def test_load_without_manifest_keeps_empty_shelf(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.load()
    assert service.items == []


def test_load_corrupt_manifest_resets_to_empty(tmp_path: Path) -> None:
    data_dir = tmp_path / "shelf"
    data_dir.mkdir(parents=True)
    (data_dir / "manifest.json").write_text("{ not valid json", encoding="utf-8")
    service = ShelfService(data_dir=data_dir, id_factory=_ids())
    service.load()
    assert service.items == []


def test_remove_does_not_unlink_image_outside_staging(tmp_path: Path) -> None:
    # An image whose path lives outside the staging dir (e.g. an externally
    # referenced file) must be removed from the shelf but never deleted on disk.
    external = tmp_path / "external.png"
    external.write_bytes(b"img")
    data_dir = tmp_path / "shelf"
    data_dir.mkdir(parents=True)
    manifest = [
        {"id": "x1", "kind": "image", "label": "external.png", "path": str(external), "text": None}
    ]
    (data_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    service = ShelfService(data_dir=data_dir, id_factory=_ids())
    service.load()

    service.remove("x1")

    assert service.items == []
    assert external.exists()


def test_open_uri_for_file_returns_file_scheme() -> None:
    item = ShelfItem(id="1", kind=ItemKind.FILE, label="report.pdf", path="/home/user/report.pdf")
    assert item.open_uri == "file:///home/user/report.pdf"


def test_open_uri_for_file_percent_encodes_spaces() -> None:
    item = ShelfItem(id="1", kind=ItemKind.FILE, label="a b.txt", path="/tmp/a b.txt")
    assert item.open_uri == "file:///tmp/a%20b.txt"


def test_open_uri_for_image_returns_file_scheme() -> None:
    item = ShelfItem(id="1", kind=ItemKind.IMAGE, label="shot.png", path="/tmp/shot.png")
    assert item.open_uri == "file:///tmp/shot.png"


def test_open_uri_for_url_returns_the_url() -> None:
    item = ShelfItem(id="1", kind=ItemKind.URL, label="x", text="https://example.com")
    assert item.open_uri == "https://example.com"


def test_open_uri_for_relative_path_is_none() -> None:
    item = ShelfItem(id="1", kind=ItemKind.FILE, label="f.txt", path="relative/f.txt")
    assert item.open_uri is None


def test_open_uri_for_text_is_none() -> None:
    item = ShelfItem(id="1", kind=ItemKind.TEXT, label="hello", text="hello")
    assert item.open_uri is None


def test_detach_all_empties_the_shelf_but_keeps_staged_images(tmp_path: Path) -> None:
    service = _service(tmp_path)
    image = service.add_image(b"png-bytes")
    assert image.path is not None

    detached = service.detach_all()

    assert service.items == []
    assert [item.id for item in detached] == [image.id]
    assert Path(image.path).exists()


def test_restore_brings_detached_items_back_in_their_order(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.add_file("/tmp/a.txt")
    service.add_url("https://gnome.org")
    detached = service.detach_all()
    service.add_text("dropped meanwhile")

    service.restore(detached)

    assert [item.label for item in service.items] == [
        "a.txt",
        "https://gnome.org",
        "dropped meanwhile",
    ]


def test_discard_deletes_staged_files_of_items_no_longer_on_the_shelf(tmp_path: Path) -> None:
    service = _service(tmp_path)
    image = service.add_image(b"png-bytes")
    assert image.path is not None
    detached = service.detach_all()

    service.discard(detached)

    assert not Path(image.path).exists()


def test_discard_keeps_staged_files_of_restored_items(tmp_path: Path) -> None:
    service = _service(tmp_path)
    image = service.add_image(b"png-bytes")
    assert image.path is not None
    detached = service.detach_all()
    service.restore(detached)

    service.discard(detached)

    assert Path(image.path).exists()


def test_a_dropped_image_is_labelled_as_an_image_not_by_its_staged_file_name(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)

    item = service.add_image(b"png-bytes")

    assert item.label == "Image"
    assert item.path is not None and Path(item.path).name != item.label


def test_load_deletes_staged_files_no_item_refers_to(tmp_path: Path) -> None:
    # A clear held for undo, then the app closed before it was committed.
    service = _service(tmp_path)
    kept = service.add_image(b"kept")
    orphan = service.add_image(b"orphan")
    assert kept.path is not None and orphan.path is not None
    service.remove(orphan.id)
    Path(orphan.path).write_bytes(b"left behind")

    reloaded = _service(tmp_path)
    reloaded.load()

    assert Path(kept.path).exists()
    assert not Path(orphan.path).exists()


def test_load_with_an_unreadable_manifest_deletes_nothing(tmp_path: Path) -> None:
    service = _service(tmp_path)
    image = service.add_image(b"png")
    assert image.path is not None
    (tmp_path / "shelf" / "manifest.json").write_text("{not json", encoding="utf-8")

    _service(tmp_path).load()

    assert Path(image.path).exists()
