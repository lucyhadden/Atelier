"""Importing images from disk."""

import pytest
from PIL import Image

from atelier.ingest import local
from atelier.ingest.images import ImageError, store_from_path


@pytest.fixture
def folder(tmp_path):
    src = tmp_path / "future-home"
    src.mkdir()
    Image.new("RGB", (2400, 1800), (200, 180, 160)).save(src / "lamp.jpg")
    Image.new("RGB", (800, 600), (180, 190, 170)).save(src / "sofa.png")
    (src / "notes.txt").write_text("not an image")
    return src


def test_import_folder_creates_a_board(db, folder, tmp_path, monkeypatch):
    monkeypatch.setenv("ATELIER_DATA_DIR", str(tmp_path / "data"))
    from atelier.config import get_settings

    get_settings.cache_clear()

    result = local.import_folder(db, folder, domain="interior")
    assert result["added"] == 2, "the .txt file must be ignored"
    assert result["board_name"] == "future home"


def test_import_is_idempotent(db, folder, tmp_path, monkeypatch):
    monkeypatch.setenv("ATELIER_DATA_DIR", str(tmp_path / "data"))
    from atelier.config import get_settings

    get_settings.cache_clear()

    local.import_folder(db, folder, domain="interior")
    again = local.import_folder(db, folder, domain="interior")
    assert again["added"] == 0
    assert again["skipped"] == 2


def test_large_images_are_downscaled(tmp_path, monkeypatch):
    monkeypatch.setenv("ATELIER_DATA_DIR", str(tmp_path / "data"))
    from atelier.config import get_settings

    get_settings.cache_clear()
    src = tmp_path / "big.jpg"
    Image.new("RGB", (4000, 3000), (10, 20, 30)).save(src)

    name = store_from_path(src)
    with Image.open(get_settings().image_dir / name) as img:
        assert max(img.size) == 1600
        assert img.format == "JPEG"


def test_unsupported_type_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("ATELIER_DATA_DIR", str(tmp_path / "data"))
    from atelier.config import get_settings

    get_settings.cache_clear()
    bad = tmp_path / "doc.pdf"
    bad.write_bytes(b"%PDF-1.4")
    with pytest.raises(ImageError):
        store_from_path(bad)


def test_empty_folder_is_an_error(db, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError):
        local.import_folder(db, empty)
