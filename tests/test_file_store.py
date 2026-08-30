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
    store.delete_final("d001", ext=".webp")
    assert not os.path.exists(final)


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
