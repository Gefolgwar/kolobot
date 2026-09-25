"""FileStore: tmp write, promote, delete, GC-tmp-only."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from kolobot.file_store import FileStore


@pytest.fixture
def store(tmp_path: Path) -> FileStore:
    return FileStore(downloads_path=str(tmp_path))


def test_save_tmp_creates_file_under_tmp_dir(store: FileStore, tmp_path: Path):
    path = store.save_tmp(b"img-bytes", ext=".jpg")
    assert os.path.isfile(path)
    assert "tmp" in path
    assert path.startswith(str(tmp_path))
    with open(path, "rb") as f:
        assert f.read() == b"img-bytes"


def test_promote_moves_tmp_to_final(store: FileStore, tmp_path: Path):
    tmp = store.save_tmp(b"data", ext=".png")
    final = store.promote(tmp, doc_id="abc123", ext=".png")

    assert not os.path.exists(tmp)
    assert os.path.isfile(final)
    assert final.endswith("abc123.png")
    rel = os.path.relpath(final, str(tmp_path))
    assert not rel.startswith("tmp")
    with open(final, "rb") as f:
        assert f.read() == b"data"


def test_delete_tmp_removes_file(store: FileStore):
    tmp = store.save_tmp(b"x", ext=".jpg")
    store.delete_tmp(tmp)
    assert not os.path.exists(tmp)


def test_delete_tmp_ignores_missing(store: FileStore):
    store.delete_tmp("/nonexistent/file.jpg")


def test_delete_final_removes_file(store: FileStore, tmp_path: Path):
    tmp = store.save_tmp(b"y", ext=".webp")
    final = store.promote(tmp, doc_id="d001", ext=".webp")
    store.save_text("d001", "Розпізнаний текст документа")
    assert os.path.exists(tmp_path / "d001.txt")
    store.delete_final("d001", ext=".webp")
    assert not os.path.exists(final)
    assert not os.path.exists(tmp_path / "d001.txt")


def test_save_and_read_text(store: FileStore, tmp_path: Path):
    txt_path = store.save_text("doc123", "Текст накладної № 45")
    assert os.path.isfile(txt_path)
    assert store.get_text_path("doc123") == txt_path
    assert store.read_text("doc123") == "Текст накладної № 45"
    assert store.read_text("nonexistent") is None
    assert store.get_text_path("nonexistent") is None


def test_delete_final_ignores_missing(store: FileStore):
    store.delete_final("nonexistent", ext=".jpg")


def test_gc_tmp_cleans_only_tmp_not_finals(store: FileStore, tmp_path: Path):
    t1 = store.save_tmp(b"tmp1", ext=".jpg")
    t2 = store.save_tmp(b"tmp2", ext=".png")
    tmp3 = store.save_tmp(b"final-data", ext=".webp")
    final = store.promote(tmp3, doc_id="keep", ext=".webp")

    store.gc_tmp()

    assert not os.path.exists(t1)
    assert not os.path.exists(t2)
    assert os.path.isfile(final)


def test_gc_tmp_on_boot_clears_only_tmp(tmp_path):
    from kolobot.file_store import FileStore
    fs = FileStore(downloads_path=str(tmp_path))
    # Create tmp and final files
    tmp_file = fs.save_tmp(b"tmp-data", ext=".jpg")
    final = tmp_path / "keep.jpg"
    final.write_bytes(b"final-data")

    fs.gc_tmp()

    assert not os.path.exists(tmp_file)
    assert os.path.isfile(str(final))
