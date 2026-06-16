from collections.abc import Callable
from pathlib import Path

from sysbar.services.shelf.models import ItemKind
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
