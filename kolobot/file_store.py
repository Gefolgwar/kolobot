"""FileStore: temp storage, promote to final, delete, startup GC."""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path


def _ext_from_mime(mime: str) -> str:
    """Map a stored MIME type to the extension used for the final file name."""
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
    }.get(mime, ".jpg")


class FileStore:
    """
    Deep module: write to downloads/tmp, promote to downloads/{doc_id}{ext},
    delete tmp/final ignore-missing, startup GC of tmp only.
    """

    def __init__(self, downloads_path: str) -> None:
        self._base = Path(downloads_path)
        self._tmp = self._base / "tmp"
        self._tmp.mkdir(parents=True, exist_ok=True)

    def save_tmp(self, data: bytes, ext: str) -> str:
        name = uuid.uuid4().hex + ext
        path = self._tmp / name
        path.write_bytes(data)
        return str(path)

    def promote(self, tmp_path: str, doc_id: str, ext: str) -> str:
        self._base.mkdir(parents=True, exist_ok=True)
        final = self._base / f"{doc_id}{ext}"
        os.replace(tmp_path, str(final))
        return str(final)

    def delete_tmp(self, path: str) -> None:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    def save_text(self, doc_id: str, text: str) -> str:
        """Save recognized OCR text directly alongside document file as {doc_id}.txt."""
        self._base.mkdir(parents=True, exist_ok=True)
        txt_path = self._base / f"{doc_id}.txt"
        txt_path.write_text(text or "", encoding="utf-8")
        return str(txt_path)

    def get_text_path(self, doc_id: str) -> str | None:
        path = self._base / f"{doc_id}.txt"
        if path.exists() and path.is_file():
            return str(path)
        return None

    def read_text(self, doc_id: str) -> str | None:
        path = self._base / f"{doc_id}.txt"
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8")
        return None

    def delete_final(self, doc_id: str, ext: str) -> None:
        path = self._base / f"{doc_id}{ext}"
        try:
            os.remove(str(path))
        except FileNotFoundError:
            pass
        txt_path = self._base / f"{doc_id}.txt"
        try:
            os.remove(str(txt_path))
        except FileNotFoundError:
            pass

    def get_final_path(self, doc_id: str, ext: str) -> str | None:
        path = self._base / f"{doc_id}{ext}"
        if path.exists() and path.is_file():
            return str(path)
        return None

    def gc_tmp(self) -> None:
        if self._tmp.exists():
            shutil.rmtree(str(self._tmp), ignore_errors=True)
            self._tmp.mkdir(parents=True, exist_ok=True)
