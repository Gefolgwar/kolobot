"""Issue #34: Telegram-повідомлення про документ, який не пішов в облік."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from kolobot.doc_structurer import Document
from kolobot.file_store import FileStore
from kolobot.main import _save_to_warehouse
from kolobot.messages import unaccounted_notice_uk
from kolobot.warehouse_db import WarehouseDB

NOT_ACCOUNTED = "Не в обліку"


@pytest.fixture
def warehouse_db(tmp_path):
    db = WarehouseDB(db_path=str(tmp_path / "warehouse.db"))
    db.init_db()
    try:
        yield db
    finally:
        db.close()


def _doc(requested_by: str = "начальник служби (ПІБ)", requested_via: str = "7939 - (ПІБ)") -> Document:
    return Document(
        doc_type="накладна",
        raw_text="НАКЛАДНА №101",
        doc_number="101",
        doc_date="01.08.2026",
        requested_by=requested_by,
        requested_via=requested_via,
        items=[{"name": "Болт М8", "nomenclature_number": "SKU-001", "unit": "шт", "quantity": "5"}],
    )


def _save(wdb: WarehouseDB, file_store: FileStore, doc: Document, existing_doc_id: Optional[int] = None) -> str:
    return _save_to_warehouse(
        wdb,
        file_store,
        doc,
        {"file_name": "nakladna_101.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "doc-1",
        existing_doc_id=existing_doc_id,
    )


def test_notice_lists_every_unrecognised_field(warehouse_db, tmp_path):
    """Блок зʼявляється з правильним переліком нерозпізнаних полів."""
    file_store = FileStore(downloads_path=str(tmp_path / "downloads"))
    msg = _save(warehouse_db, file_store, _doc(requested_by="", requested_via=""))

    assert NOT_ACCOUNTED in msg
    assert "не розпізнано: Затребував, Через кого." in msg
    assert "не враховано в залишках" in msg


def test_notice_lists_only_the_empty_fields(warehouse_db, tmp_path):
    """Повний перелік — саме порожні поля, а не всі обовʼязкові."""
    file_store = FileStore(downloads_path=str(tmp_path / "downloads"))
    msg = _save(warehouse_db, file_store, _doc(requested_via=""))

    assert "не розпізнано: Через кого." in msg
    assert "Затребував" not in msg


def test_notice_does_not_touch_the_positions_line(warehouse_db, tmp_path):
    """Рядок про кількість позицій і транзакцій лишається незмінним."""
    file_store = FileStore(downloads_path=str(tmp_path / "downloads"))
    msg = _save(warehouse_db, file_store, _doc(requested_by="", requested_via=""))

    assert msg.startswith("📦 Склад: 1 нових позицій, 1 транзакцій.")


def test_no_notice_for_fully_recognised_document(warehouse_db, tmp_path):
    """Для повністю розпізнаного документа блок не зʼявляється."""
    file_store = FileStore(downloads_path=str(tmp_path / "downloads"))
    msg = _save(warehouse_db, file_store, _doc())

    assert msg == "📦 Склад: 1 нових позицій, 1 транзакцій."
    assert NOT_ACCOUNTED not in msg


@pytest.mark.parametrize("file_type", ["excel", "manual"])
def test_no_notice_for_non_ocr_documents(file_type):
    """Excel і системний документ ручних коригувань не мають полів бланка — блока немає."""
    empty_form: Dict[str, Any] = {
        "file_type": file_type,
        "doc_type": "",
        "doc_number": "",
        "doc_date": "",
        "requested_by": "",
        "requested_via": "",
    }
    assert unaccounted_notice_uk(empty_form) == ""
