"""Issue #33: попередження про втрату ручних правок і скидання позначки при повторі."""

from __future__ import annotations

from typing import Optional

import pytest

from kolobot.doc_structurer import Document
from kolobot.file_store import FileStore
from kolobot.main import _save_to_warehouse
from kolobot.warehouse_db import WarehouseDB


@pytest.fixture
def warehouse_db(tmp_path):
    db = WarehouseDB(db_path=str(tmp_path / "warehouse.db"))
    db.init_db()
    try:
        yield db
    finally:
        db.close()


def _doc(quantity: str = "5") -> Document:
    return Document(
        doc_type="накладна",
        raw_text="НАКЛАДНА №101",
        doc_number="101",
        doc_date="01.08.2026",
        requested_by="начальник служби (ПІБ)",
        requested_via="7939 - (ПІБ)",
        items=[{"name": "Болт М8", "nomenclature_number": "SKU-001", "unit": "шт", "quantity": quantity}],
    )


def _save(
    wdb: WarehouseDB,
    file_store: FileStore,
    doc: Optional[Document] = None,
    existing_doc_id: Optional[int] = None,
) -> int:
    """Зберігає документ і повертає його id у складі."""
    _save_to_warehouse(
        wdb,
        file_store,
        doc or _doc(),
        {"file_name": "nakladna_101.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "doc-1",
        existing_doc_id=existing_doc_id,
    )
    return wdb.get_documents()[0]["id"]


def _only_item_id(wdb: WarehouseDB) -> int:
    return wdb.get_items_with_balance()[0]["id"]


def test_repeat_resets_the_manual_edit_flag(warehouse_db, tmp_path):
    """Після повтору значення документа знову машинні — позначки ручної правки немає."""
    file_store = FileStore(downloads_path=str(tmp_path / "downloads"))
    doc_id = _save(warehouse_db, file_store)

    warehouse_db.edit_document_field(doc_id, "requested_by", "комірник (ПІБ)")
    assert warehouse_db.get_document(doc_id)["manual_edited"] == 1

    _save(warehouse_db, file_store, existing_doc_id=doc_id)

    doc = warehouse_db.get_document(doc_id)
    assert doc["manual_edited"] == 0
    assert doc["requested_by"] == "начальник служби (ПІБ)"
    assert doc["status"] == "completed"


def test_repeat_erases_the_edit_mark_in_documents_and_warehouse_tabs(warehouse_db, tmp_path):
    """Позначку знято в обох вкладках: і в «Документах», і на рядку документа у «Складі»."""
    file_store = FileStore(downloads_path=str(tmp_path / "downloads"))
    doc_id = _save(warehouse_db, file_store)
    item_id = _only_item_id(warehouse_db)

    warehouse_db.edit_document_field(doc_id, "requested_by", "комірник (ПІБ)")
    assert warehouse_db.get_item_transactions(item_id)[0]["manual_edited"] is True

    _save(warehouse_db, file_store, existing_doc_id=doc_id)

    docs = {d["id"]: d for d in warehouse_db.get_documents()}
    assert docs[doc_id]["manual_edited"] is False
    assert warehouse_db.get_item_transactions(item_id)[0]["manual_edited"] is False


def test_repeat_rewrites_the_values_and_does_not_double_the_transactions(warehouse_db, tmp_path):
    """Скидання позначки їде разом зі справжнім повторним записом, а не замість нього."""
    file_store = FileStore(downloads_path=str(tmp_path / "downloads"))
    doc_id = _save(warehouse_db, file_store, _doc(quantity="5"))
    item_id = _only_item_id(warehouse_db)

    _save(warehouse_db, file_store, _doc(quantity="8"), existing_doc_id=doc_id)

    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 1
    assert txs[0]["quantity"] == 8.0
    assert warehouse_db.get_items_with_balance()[0]["balance"] == 8.0
