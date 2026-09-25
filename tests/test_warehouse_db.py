"""Unit tests for WarehouseDB item metadata adjustment and audit logging."""

from __future__ import annotations

import datetime
import sqlite3

import pytest

from kolobot.warehouse_db import REQUIRED_DOC_FIELDS, WarehouseDB, missing_doc_fields


@pytest.fixture
def warehouse_db(tmp_path):
    db_path = str(tmp_path / "warehouse.db")
    db = WarehouseDB(db_path=db_path)
    db.init_db()
    try:
        yield db
    finally:
        db.close()


def _add_complete_photo_doc(db, **overrides):
    """OCR-документ, у якого розпізнано всі пʼять обовʼязкових полів бланка."""
    fields = {
        "filename": "nakladna_101.jpg",
        "file_type": "photo",
        "doc_type": "НАКЛАДНА",
        "doc_number": "101",
        "doc_date": "01.08.2026",
        "requested_by": "начальник служби (ПІБ)",
        "requested_via": "7939 - (ПІБ)",
    }
    fields.update(overrides)
    return db.add_document(**fields)


def _add_incomplete_photo_doc(db, **overrides):
    """OCR-документ, у якому не розпізнано «Затребував»."""
    return _add_complete_photo_doc(db, filename="vymoha_incomplete.jpg", requested_by="", **overrides)


def test_adjust_item_field_name_creates_audit_transaction(warehouse_db):
    # 1. Add initial doc and item
    doc_id = warehouse_db.add_document(
        filename="nakladna_1.xlsx",
        file_type="excel",
        doc_type="НАКЛАДНА",
        doc_number="101",
        doc_date="01.08.2026",
    )
    item_id = warehouse_db.add_item(
        name="Болт М8",
        sku="SKU-001",
        unit="шт",
        supplier="ТОВ Постач",
        notes="Стандартний",
    )
    warehouse_db.add_transaction(
        item_id=item_id,
        document_id=doc_id,
        operation_type="income",
        quantity=50.0,
        doc_number="101",
        doc_date="01.08.2026",
    )

    # 2. Adjust name
    result = warehouse_db.adjust_item_field(
        item_id=item_id,
        field="name",
        new_value="Болт М8х30 Оцинкований",
        comment="Уточнення розміру",
    )

    assert result is not None
    assert result["success"] is True
    assert result["item"]["name"] == "Болт М8х30 Оцинкований"
    assert result["old_value"] == "Болт М8"
    assert result["new_value"] == "Болт М8х30 Оцинкований"

    # 3. Verify item updated in DB
    item = warehouse_db.find_item(name="Болт М8х30 Оцинкований")
    assert item is not None
    assert item["id"] == item_id

    # 4. Verify balance is preserved
    items = warehouse_db.get_items_with_balance()
    assert len(items) == 1
    assert items[0]["name"] == "Болт М8х30 Оцинкований"
    assert items[0]["total_income"] == 50.0
    assert items[0]["total_expense"] == 0.0
    assert items[0]["balance"] == 50.0

    # 5. Verify audit transaction in item transaction history
    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 2

    # Second transaction is the zero-quantity audit record
    audit_tx = txs[1]
    assert audit_tx["quantity"] == 0.0
    assert audit_tx["operation_type"] == "income"
    assert audit_tx["running_balance"] == 50.0
    assert audit_tx["doc_type"] == "РУЧНЕ_КОРИГУВАННЯ"
    assert audit_tx["filename"] == "Ручне редагування (Користувач)"
    assert audit_tx["file_type"] == "manual"
    assert "Змінено [Найменування]: 'Болт М8' → 'Болт М8х30 Оцинкований'" in audit_tx["source_row"]
    assert "Уточнення розміру" in audit_tx["source_row"]


def test_adjust_item_other_fields(warehouse_db):
    item_id = warehouse_db.add_item(
        name="Гайка М6",
        sku="OLD-SKU",
        unit="шт",
        supplier="Старий Постачальник",
        notes="Стара примітка",
    )
    doc_id = warehouse_db.add_document(filename="init.xlsx", file_type="excel")
    warehouse_db.add_transaction(item_id=item_id, document_id=doc_id, operation_type="income", quantity=100.0)

    # Adjust SKU
    res_sku = warehouse_db.adjust_item_field(item_id=item_id, field="sku", new_value="NEW-SKU-999")
    assert res_sku["success"] is True
    assert "Змінено [Номенклатурний номер]: 'OLD-SKU' → 'NEW-SKU-999'" in res_sku["source_row"]

    # Adjust Unit
    res_unit = warehouse_db.adjust_item_field(item_id=item_id, field="unit", new_value="компл")
    assert res_unit["success"] is True
    assert "Змінено [Од. виміру]: 'шт' → 'компл'" in res_unit["source_row"]

    # Adjust Supplier
    res_sup = warehouse_db.adjust_item_field(item_id=item_id, field="supplier", new_value="Новий Постачальник")
    assert res_sup["success"] is True
    assert "Змінено [Постачальник]: 'Старий Постачальник' → 'Новий Постачальник'" in res_sup["source_row"]

    # Adjust Notes
    res_not = warehouse_db.adjust_item_field(item_id=item_id, field="notes", new_value="Оновлена примітка")
    assert res_not["success"] is True
    assert "Змінено [Примітки]: 'Стара примітка' → 'Оновлена примітка'" in res_not["source_row"]

    # Verify transactions count
    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 5  # 1 initial + 4 adjustments
    assert all(tx["running_balance"] == 100.0 for tx in txs[1:])


def test_adjust_item_field_reuses_manual_document(warehouse_db):
    item1_id = warehouse_db.add_item(name="Item 1")
    item2_id = warehouse_db.add_item(name="Item 2")
    doc_id = warehouse_db.add_document(filename="init.xlsx", file_type="excel")
    warehouse_db.add_transaction(item_id=item1_id, document_id=doc_id, operation_type="income", quantity=10)
    warehouse_db.add_transaction(item_id=item2_id, document_id=doc_id, operation_type="income", quantity=20)

    warehouse_db.adjust_item_field(item_id=item1_id, field="name", new_value="Item 1 Edited")
    warehouse_db.adjust_item_field(item_id=item2_id, field="name", new_value="Item 2 Edited")

    docs = warehouse_db.get_documents()
    manual_docs = [d for d in docs if d["doc_type"] == "РУЧНЕ_КОРИГУВАННЯ"]
    assert len(manual_docs) == 1
    assert manual_docs[0]["transaction_count"] == 2


def test_adjust_item_field_nonexistent_and_invalid(warehouse_db):
    # Nonexistent item
    res_none = warehouse_db.adjust_item_field(item_id=9999, field="name", new_value="Test")
    assert res_none is None

    # Invalid field
    item_id = warehouse_db.add_item(name="Valid Item")
    with pytest.raises(ValueError, match="Invalid field"):
        warehouse_db.adjust_item_field(item_id=item_id, field="balance", new_value="100")


def test_adjust_item_quantity_positive_delta_creates_income_transaction(warehouse_db):
    # Initial balance: 50
    doc_id = warehouse_db.add_document(filename="init.xlsx", file_type="excel")
    item_id = warehouse_db.add_item(name="Кабель ВВГ", sku="CAB-01", unit="м")
    warehouse_db.add_transaction(item_id=item_id, document_id=doc_id, operation_type="income", quantity=50.0)

    # Adjust target quantity to 80 (delta = +30)
    result = warehouse_db.adjust_item_quantity(
        item_id=item_id,
        target_quantity=80.0,
        comment="Перерахунок залишку",
    )

    assert result is not None
    assert result["success"] is True
    assert result["old_balance"] == 50.0
    assert result["target_quantity"] == 80.0
    assert result["delta"] == 30.0
    assert result["operation_type"] == "income"
    assert result["transaction_id"] is not None
    assert "Змінено 'Кількість': 50 → 80 (Перерахунок залишку)" in result["source_row"]

    # Verify balance reconciliation
    items = warehouse_db.get_items_with_balance()
    cab = next(i for i in items if i["id"] == item_id)
    assert cab["total_income"] == 80.0
    assert cab["total_expense"] == 0.0
    assert cab["balance"] == 80.0

    # Verify transactions history
    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 2
    adj_tx = txs[1]
    assert adj_tx["quantity"] == 30.0
    assert adj_tx["operation_type"] == "income"
    assert adj_tx["running_balance"] == 80.0
    assert adj_tx["doc_type"] == "РУЧНЕ_КОРИГУВАННЯ"
    assert adj_tx["filename"] == "Ручне редагування (Користувач)"


def test_adjust_item_quantity_negative_delta_creates_expense_transaction(warehouse_db):
    # Initial balance: 100
    doc_id = warehouse_db.add_document(filename="init.xlsx", file_type="excel")
    item_id = warehouse_db.add_item(name="Труба ПВХ", sku="TR-01", unit="м")
    warehouse_db.add_transaction(item_id=item_id, document_id=doc_id, operation_type="income", quantity=100.0)

    # Adjust target quantity to 65 (delta = -35 -> expense of 35)
    result = warehouse_db.adjust_item_quantity(
        item_id=item_id,
        target_quantity=65.0,
        comment="Списання браку",
    )

    assert result is not None
    assert result["success"] is True
    assert result["old_balance"] == 100.0
    assert result["target_quantity"] == 65.0
    assert result["delta"] == -35.0
    assert result["operation_type"] == "expense"
    assert result["transaction_id"] is not None
    assert "Змінено 'Кількість': 100 → 65 (Списання браку)" in result["source_row"]

    # Verify balance reconciliation
    items = warehouse_db.get_items_with_balance()
    pipe = next(i for i in items if i["id"] == item_id)
    assert pipe["total_income"] == 100.0
    assert pipe["total_expense"] == 35.0
    assert pipe["balance"] == 65.0

    # Verify transactions history
    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 2
    adj_tx = txs[1]
    assert adj_tx["quantity"] == 35.0
    assert adj_tx["operation_type"] == "expense"
    assert adj_tx["running_balance"] == 65.0


def test_adjust_item_quantity_zero_delta_no_transaction(warehouse_db):
    doc_id = warehouse_db.add_document(filename="init.xlsx", file_type="excel")
    item_id = warehouse_db.add_item(name="Лампа LED", sku="LED-01", unit="шт")
    warehouse_db.add_transaction(item_id=item_id, document_id=doc_id, operation_type="income", quantity=20.0)

    # Target is same as current balance (20.0)
    result = warehouse_db.adjust_item_quantity(
        item_id=item_id,
        target_quantity=20.0,
        comment="Без змін",
    )

    assert result is not None
    assert result["success"] is True
    assert result["delta"] == 0.0
    assert result["transaction_id"] is None

    # Verify no new transaction was created
    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 1


def test_adjust_item_quantity_nonexistent_item(warehouse_db):
    result = warehouse_db.adjust_item_quantity(item_id=99999, target_quantity=10.0)
    assert result is None


def test_get_items_with_balance_doc_count(warehouse_db):
    # Item 1 has an excel doc transaction
    doc_id = warehouse_db.add_document(filename="init.xlsx", file_type="excel")
    item1_id = warehouse_db.add_item(name="Item With Doc", sku="SKU-1")
    warehouse_db.add_transaction(item_id=item1_id, document_id=doc_id, operation_type="income", quantity=10.0)

    # Item 2 has only manual adjustment transactions (no non-manual docs)
    item2_id = warehouse_db.add_item(name="Item Manual Only", sku="SKU-2")
    warehouse_db.adjust_item_quantity(item_id=item2_id, target_quantity=5.0)

    # Item 3 has no transactions at all
    item3_id = warehouse_db.add_item(name="Item No Tx", sku="SKU-3")

    items = warehouse_db.get_items_with_balance()
    items_map = {it["id"]: it for it in items}

    assert items_map[item1_id]["doc_count"] == 1
    assert items_map[item2_id]["doc_count"] == 0
    assert items_map[item3_id]["doc_count"] == 0


def test_adjust_item_field_min_balance(warehouse_db):
    item_id = warehouse_db.add_item(
        name="Гайка М8",
        sku="NUT-M8",
        min_balance=0.0,
    )

    # 1. Adjust min_balance to 25.0
    res = warehouse_db.adjust_item_field(item_id=item_id, field="min_balance", new_value=25.0, comment="Норма запасу")
    assert res is not None
    assert res["success"] is True
    assert res["new_value"] == 25.0
    assert "Змінено [Мінімальний залишок]: '0' → '25'" in res["source_row"]
    assert "Норма запасу" in res["source_row"]

    # 2. Check item from find_item and get_item
    item = warehouse_db.get_item(item_id)
    assert item["min_balance"] == 25.0

    # 3. Check get_items_with_balance
    items = warehouse_db.get_items_with_balance()
    assert len(items) == 1
    assert items[0]["min_balance"] == 25.0

    # 4. Check audit transaction
    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 1
    assert txs[0]["doc_type"] == "РУЧНЕ_КОРИГУВАННЯ"
    assert txs[0]["quantity"] == 0.0


def test_add_item_with_min_balance(warehouse_db):
    item_id = warehouse_db.add_item(
        name="Шайба М10",
        sku="WASH-10",
        min_balance=100.0,
    )
    item = warehouse_db.get_item(item_id)
    assert item["min_balance"] == 100.0

    items = warehouse_db.get_items_with_balance()
    assert items[0]["min_balance"] == 100.0


def test_init_db_migrates_legacy_documents_to_completed_status(tmp_path):
    """Existing DBs without status columns: old rows must become 'completed'."""
    db_path = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL DEFAULT '',
            uploaded_at REAL NOT NULL,
            doc_number TEXT NOT NULL DEFAULT '',
            doc_date TEXT NOT NULL DEFAULT '',
            raw_text TEXT NOT NULL DEFAULT '',
            doc_type TEXT NOT NULL DEFAULT ''
        );
    """)
    conn.execute(
        "INSERT INTO documents (filename, file_type, uploaded_at) VALUES (?, ?, ?)",
        ("legacy.jpg", "photo", 1.0),
    )
    conn.commit()
    conn.close()

    db = WarehouseDB(db_path=db_path)
    db.init_db()
    try:
        doc = db.get_document(1)
        assert doc["status"] == "completed"
        assert doc["error_message"] == ""
    finally:
        db.close()


def test_add_document_registers_queued_status_with_saved_file_path(warehouse_db):
    doc_id = warehouse_db.add_document(
        filename="nakladna_1.jpg",
        file_type="photo",
        file_path="/downloads/tmp/a1b2c3.jpg",
        status="queued",
    )

    doc = warehouse_db.get_document(doc_id)
    assert doc["status"] == "queued"
    assert doc["error_message"] == ""
    assert doc["file_path"] == "/downloads/tmp/a1b2c3.jpg"

    docs = warehouse_db.get_documents()
    assert len(docs) == 1
    assert docs[0]["status"] == "queued"


def test_update_document_completes_queued_record_in_place(warehouse_db):
    doc_id = warehouse_db.add_document(
        filename="photo.jpg",
        file_type="photo",
        file_path="/downloads/tmp/a1b2c3.jpg",
        status="queued",
    )

    updated = warehouse_db.update_document(
        doc_id,
        file_path="/downloads/abcdef1234.jpg",
        doc_number="101",
        doc_date="01.08.2026",
        doc_type="НАКЛАДНА",
        raw_text="НАКЛАДНА № 101",
        status="completed",
    )

    assert updated is True
    assert len(warehouse_db.get_documents()) == 1

    doc = warehouse_db.get_document(doc_id)
    assert doc["status"] == "completed"
    assert doc["file_path"] == "/downloads/abcdef1234.jpg"
    assert doc["doc_number"] == "101"
    assert doc["doc_type"] == "НАКЛАДНА"
    assert doc["raw_text"] == "НАКЛАДНА № 101"


def test_update_document_unknown_id_returns_false(warehouse_db):
    assert warehouse_db.update_document(9999, status="completed") is False


def test_add_document_persists_requested_by(warehouse_db):
    """Затребувач зберігається в документі і віддається в списку документів."""
    doc_id = warehouse_db.add_document(
        filename="nakladna_1.jpg",
        file_type="photo",
        requested_by="начальник служби (ПІБ)",
    )

    doc = warehouse_db.get_document(doc_id)
    assert doc["requested_by"] == "начальник служби (ПІБ)"

    docs = warehouse_db.get_documents()
    assert docs[0]["requested_by"] == "начальник служби (ПІБ)"


def test_update_document_can_set_requested_by(warehouse_db):
    """Затребувач дописується у вже наявний документ (напр. після повторного розпізнавання)."""
    doc_id = warehouse_db.add_document(filename="nakladna_2.jpg", file_type="photo")

    assert warehouse_db.update_document(doc_id, requested_by="механік (ПІБ)") is True
    assert warehouse_db.get_document(doc_id)["requested_by"] == "механік (ПІБ)"


def test_item_transactions_expose_document_requested_by(warehouse_db):
    """У розгорнутому рядку позиції (Склад) видно, хто затребував кожен документ."""
    doc_id = warehouse_db.add_document(
        filename="vymoha.jpg",
        file_type="photo",
        doc_type="ВИМОГА",
        requested_by="начальник служби (ПІБ)",
    )
    item_id = warehouse_db.add_item(name="Болт М8", sku="SKU-001", unit="шт")
    warehouse_db.add_transaction(
        item_id=item_id,
        document_id=doc_id,
        operation_type="expense",
        quantity=5.0,
    )

    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 1
    assert txs[0]["requested_by"] == "начальник служби (ПІБ)"


def test_add_document_persists_requested_via(warehouse_db):
    """'Через кого' зберігається в документі і віддається в списку документів."""
    doc_id = warehouse_db.add_document(
        filename="nakladna_1.jpg",
        file_type="photo",
        requested_via="7939 - (ПІБ)",
    )

    doc = warehouse_db.get_document(doc_id)
    assert doc["requested_via"] == "7939 - (ПІБ)"

    docs = warehouse_db.get_documents()
    assert docs[0]["requested_via"] == "7939 - (ПІБ)"


def test_update_document_can_set_requested_via(warehouse_db):
    """'Через кого' дописується у вже наявний документ (напр. після повторного розпізнавання)."""
    doc_id = warehouse_db.add_document(filename="nakladna_2.jpg", file_type="photo")

    assert warehouse_db.update_document(doc_id, requested_via="6461 - механік (ПІБ)") is True
    assert warehouse_db.get_document(doc_id)["requested_via"] == "6461 - механік (ПІБ)"


def test_item_transactions_expose_document_requested_via(warehouse_db):
    """У розгорнутому рядку позиції (Склад) видно, через кого отримано кожен документ."""
    doc_id = warehouse_db.add_document(
        filename="vymoha.jpg",
        file_type="photo",
        doc_type="ВИМОГА",
        requested_via="7939 - (ПІБ)",
    )
    item_id = warehouse_db.add_item(name="Болт М8", sku="SKU-001", unit="шт")
    warehouse_db.add_transaction(
        item_id=item_id,
        document_id=doc_id,
        operation_type="expense",
        quantity=5.0,
    )

    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 1
    assert txs[0]["requested_via"] == "7939 - (ПІБ)"


def test_migration_backfills_requester_fields_from_existing_raw_text(tmp_path):
    """Документи, збережені до появи полів, отримують затребувача і 'через кого' зі свого OCR-тексту."""
    db_path = str(tmp_path / "legacy.db")

    # БД попередньої версії: колонок requested_by / requested_via ще немає.
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL DEFAULT '',
            uploaded_at REAL NOT NULL,
            doc_number TEXT NOT NULL DEFAULT '',
            doc_date TEXT NOT NULL DEFAULT '',
            raw_text TEXT NOT NULL DEFAULT '',
            doc_type TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE warehouse_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            unit TEXT NOT NULL DEFAULT '',
            supplier TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE warehouse_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL REFERENCES warehouse_items(id),
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            operation_type TEXT NOT NULL CHECK(operation_type IN ('income', 'expense')),
            quantity REAL NOT NULL DEFAULT 0,
            doc_number TEXT NOT NULL DEFAULT '',
            doc_date TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL
        );
    """)
    conn.execute(
        "INSERT INTO documents (filename, file_type, uploaded_at, raw_text, doc_type) VALUES (?, ?, ?, ?, ?)",
        (
            "old_nakladna.jpg",
            "photo",
            1.0,
            "НАКЛАДНА № 0002143\nЧЕРЕЗ КОГО 7939 - (ПІБ)\nЗАТРЕБУВАВ: начальник служби (ПІБ)\nБУХГАЛТЕР:",
            "НАКЛАДНА",
        ),
    )
    conn.execute(
        "INSERT INTO documents (filename, file_type, uploaded_at, raw_text, doc_type) VALUES (?, ?, ?, ?, ?)",
        ("old_excel.xlsx", "excel", 2.0, "", ""),
    )
    conn.commit()
    conn.close()

    db = WarehouseDB(db_path=db_path)
    db.init_db()
    try:
        docs = {d["filename"]: d for d in db.get_documents()}
        assert docs["old_nakladna.jpg"]["requested_by"] == "начальник служби (ПІБ)"
        assert docs["old_nakladna.jpg"]["requested_via"] == "7939 - (ПІБ)"
        assert docs["old_excel.xlsx"]["requested_by"] == ""
        assert docs["old_excel.xlsx"]["requested_via"] == ""
    finally:
        db.close()


def test_migration_handles_db_that_already_has_requested_by(tmp_path):
    """БД, мігрована попередньою версією (є requested_by, немає requested_via), дозаповнюється коректно."""
    db_path = str(tmp_path / "half_migrated.db")

    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL DEFAULT '',
            uploaded_at REAL NOT NULL,
            doc_number TEXT NOT NULL DEFAULT '',
            doc_date TEXT NOT NULL DEFAULT '',
            raw_text TEXT NOT NULL DEFAULT '',
            doc_type TEXT NOT NULL DEFAULT '',
            requested_by TEXT NOT NULL DEFAULT ''
        );
    """)
    conn.execute(
        "INSERT INTO documents (filename, file_type, uploaded_at, raw_text, requested_by) VALUES (?, ?, ?, ?, ?)",
        (
            "half.jpg",
            "photo",
            1.0,
            "НАКЛАДНА № 1\nЧЕРЕЗ КОГО 7939 - (ПІБ)\nЗАТРЕБУВАВ: начальник служби (ПІБ)",
            "",
        ),
    )
    conn.commit()
    conn.close()

    db = WarehouseDB(db_path=db_path)
    db.init_db()
    try:
        doc = db.get_documents()[0]
        assert doc["requested_by"] == "начальник служби (ПІБ)"
        assert doc["requested_via"] == "7939 - (ПІБ)"
    finally:
        db.close()


# =========================================================================
# Неповне розпізнавання: «не в обліку» (Issue #28)
# =========================================================================


def test_missing_doc_fields_lists_empty_required_fields(warehouse_db):
    """Хелпер віддає назви саме порожніх обовʼязкових полів бланка."""
    complete_id = _add_complete_photo_doc(warehouse_db)
    partial_id = _add_complete_photo_doc(
        warehouse_db, filename="partial.jpg", doc_number="", requested_via="   "
    )

    docs = {d["id"]: d for d in warehouse_db.get_documents()}
    assert docs[complete_id]["missing_fields"] == []
    assert docs[partial_id]["missing_fields"] == ["№ документа", "Через кого"]


def test_missing_doc_fields_is_empty_for_excel_and_manual_documents(warehouse_db):
    """Excel-імпорт і системний документ ручних коригувань під правило не підпадають."""
    excel_doc = {"file_type": "excel", "doc_type": "", "doc_number": "", "doc_date": "",
                 "requested_by": "", "requested_via": ""}
    manual_doc = {"file_type": "manual", "doc_type": "РУЧНЕ_КОРИГУВАННЯ", "doc_number": "",
                  "doc_date": "", "requested_by": "", "requested_via": ""}
    photo_doc = {"file_type": "photo", "doc_type": "", "doc_number": "1", "doc_date": "",
                 "requested_by": "", "requested_via": ""}

    assert missing_doc_fields(excel_doc) == []
    assert missing_doc_fields(manual_doc) == []
    assert missing_doc_fields(photo_doc) == ["Тип документу", "Дата документа", "Затребував", "Через кого"]


def test_missing_doc_fields_reports_every_required_field_name(warehouse_db):
    """Усі пʼять обовʼязкових полів походять з єдиного переліку."""
    empty_doc = {"file_type": "photo"}
    assert missing_doc_fields(empty_doc) == [label for label, _ in REQUIRED_DOC_FIELDS]

    excel_id = warehouse_db.add_document(filename="import.xlsx", file_type="excel")
    manual_id = warehouse_db.get_or_create_manual_document()
    docs = {d["id"]: d for d in warehouse_db.get_documents()}
    assert docs[excel_id]["missing_fields"] == []
    assert docs[manual_id]["missing_fields"] == []


@pytest.mark.parametrize("column", [column for _, column in REQUIRED_DOC_FIELDS])
def test_every_required_field_gates_accounting(warehouse_db, column):
    """Порожнє будь-яке з пʼяти полів виводить документ з обліку, заповнене — повертає."""
    filled = "01.08.2026" if column == "doc_date" else "НАКЛАДНА"
    doc_id = _add_complete_photo_doc(warehouse_db, **{column: ""})
    item_id = warehouse_db.add_item(name="Болт М8", sku="SKU-001", unit="шт")
    warehouse_db.add_transaction(
        item_id=item_id, document_id=doc_id, operation_type="income", quantity=10.0
    )

    assert warehouse_db.get_item_balance(item_id) == 0.0
    assert warehouse_db.get_item_transactions(item_id)[0]["accounted"] is False

    warehouse_db.update_document(doc_id, **{column: filled})

    assert warehouse_db.get_item_balance(item_id) == 10.0
    assert warehouse_db.get_item_transactions(item_id)[0]["accounted"] is True


def test_incomplete_document_does_not_affect_income_expense_and_balance(warehouse_db):
    """Прихід, розхід і залишок позиції рахують лише повністю розпізнані документи."""
    item_id = warehouse_db.add_item(name="Кабель ВВГ", sku="CAB-01", unit="м")
    complete_doc = _add_complete_photo_doc(warehouse_db)
    incomplete_doc = _add_incomplete_photo_doc(warehouse_db)

    warehouse_db.add_transaction(
        item_id=item_id, document_id=complete_doc, operation_type="income", quantity=50.0
    )
    warehouse_db.add_transaction(
        item_id=item_id, document_id=incomplete_doc, operation_type="income", quantity=105.0
    )
    warehouse_db.add_transaction(
        item_id=item_id, document_id=incomplete_doc, operation_type="expense", quantity=7.0
    )

    item = next(i for i in warehouse_db.get_items_with_balance() if i["id"] == item_id)
    assert item["total_income"] == 50.0
    assert item["total_expense"] == 0.0
    assert item["balance"] == 50.0


def test_incomplete_document_is_not_counted_and_item_falls_out_of_doc_count(warehouse_db):
    """Позиція з єдиним необлікованим документом показує 0 документів."""
    item_id = warehouse_db.add_item(name="Труба ПВХ", sku="TR-01", unit="м")
    incomplete_doc = _add_incomplete_photo_doc(warehouse_db)
    warehouse_db.add_transaction(
        item_id=item_id, document_id=incomplete_doc, operation_type="income", quantity=30.0
    )

    item = next(i for i in warehouse_db.get_items_with_balance() if i["id"] == item_id)
    assert item["doc_count"] == 0
    assert item["balance"] == 0.0

    warehouse_db.update_document(incomplete_doc, requested_by="комірник (ПІБ)")

    item = next(i for i in warehouse_db.get_items_with_balance() if i["id"] == item_id)
    assert item["doc_count"] == 1
    assert item["balance"] == 30.0


def test_last_doc_date_and_number_skip_unaccounted_transactions(warehouse_db):
    """Остання дата й номер позиції беруться лише з урахованих транзакцій."""
    item_id = warehouse_db.add_item(name="Лампа LED", sku="LED-01", unit="шт")
    complete_doc = _add_complete_photo_doc(warehouse_db, doc_number="101", doc_date="01.08.2026")
    incomplete_doc = _add_incomplete_photo_doc(warehouse_db, doc_number="999", doc_date="31.12.2026")

    warehouse_db.add_transaction(
        item_id=item_id, document_id=complete_doc, operation_type="income",
        quantity=10.0, doc_number="101", doc_date="01.08.2026",
    )
    warehouse_db.add_transaction(
        item_id=item_id, document_id=incomplete_doc, operation_type="income",
        quantity=99.0, doc_number="999", doc_date="31.12.2026",
    )

    item = next(i for i in warehouse_db.get_items_with_balance() if i["id"] == item_id)
    assert item["last_doc_number"] == "101"
    assert item["last_doc_date"] == "01.08.2026"


def test_manual_quantity_adjustment_ignores_unaccounted_transactions(warehouse_db):
    """База для ручного коригування залишку не враховує необліковані транзакції."""
    item_id = warehouse_db.add_item(name="Шайба М10", sku="WASH-10", unit="шт")
    incomplete_doc = _add_incomplete_photo_doc(warehouse_db)
    warehouse_db.add_transaction(
        item_id=item_id, document_id=incomplete_doc, operation_type="income", quantity=105.0
    )

    result = warehouse_db.adjust_item_quantity(item_id=item_id, target_quantity=20.0)

    assert result["old_balance"] == 0.0
    assert result["delta"] == 20.0
    assert result["operation_type"] == "income"
    assert warehouse_db.get_item_balance(item_id) == 20.0


def test_running_balance_skips_unaccounted_rows_and_matches_item_balance(warehouse_db):
    """Накопичувальний залишок в історії пропускає невраховані рядки й збігається із залишком позиції."""
    item_id = warehouse_db.add_item(name="Гайка М6", sku="NUT-M6", unit="шт")
    complete_doc = _add_complete_photo_doc(warehouse_db)
    incomplete_doc = _add_incomplete_photo_doc(warehouse_db)

    warehouse_db.add_transaction(
        item_id=item_id, document_id=complete_doc, operation_type="income", quantity=10.0
    )
    warehouse_db.add_transaction(
        item_id=item_id, document_id=incomplete_doc, operation_type="income", quantity=100.0
    )
    warehouse_db.add_transaction(
        item_id=item_id, document_id=complete_doc, operation_type="expense", quantity=4.0
    )

    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 3
    assert [tx["accounted"] for tx in txs] == [True, False, True]
    assert [tx["running_balance"] for tx in txs] == [10.0, 10.0, 6.0]

    item = next(i for i in warehouse_db.get_items_with_balance() if i["id"] == item_id)
    assert txs[-1]["running_balance"] == item["balance"] == 6.0


def test_filling_a_field_returns_document_to_accounting_without_extra_actions(warehouse_db):
    """Дозаповнення поля прямо в базі повертає документ в облік; стирання — виводить."""
    item_id = warehouse_db.add_item(name="Болт М8", sku="SKU-001", unit="шт")
    doc_id = _add_incomplete_photo_doc(warehouse_db)
    warehouse_db.add_transaction(
        item_id=item_id, document_id=doc_id, operation_type="income", quantity=105.0
    )

    assert warehouse_db.get_item_balance(item_id) == 0.0

    warehouse_db.update_document(doc_id, requested_by="начальник служби (ПІБ)")

    assert warehouse_db.get_item_balance(item_id) == 105.0
    assert warehouse_db.get_document(doc_id)["requested_by"] == "начальник служби (ПІБ)"

    warehouse_db.update_document(doc_id, requested_by="")

    assert warehouse_db.get_item_balance(item_id) == 0.0
    item = next(i for i in warehouse_db.get_items_with_balance() if i["id"] == item_id)
    assert item["doc_count"] == 0


def test_documents_selection_reports_missing_fields_and_manual_edit_mark(warehouse_db):
    """Вибірка документів віддає перелік відсутніх полів і позначку ручного редагування."""
    complete_doc = _add_complete_photo_doc(warehouse_db)
    incomplete_doc = _add_incomplete_photo_doc(warehouse_db)
    excel_doc = warehouse_db.add_document(filename="import.xlsx", file_type="excel")

    docs = {d["id"]: d for d in warehouse_db.get_documents()}
    assert docs[complete_doc]["missing_fields"] == []
    assert docs[complete_doc]["manual_edited"] is False
    assert docs[incomplete_doc]["missing_fields"] == ["Затребував"]
    assert docs[excel_doc]["missing_fields"] == []

    warehouse_db.update_document(incomplete_doc, manual_edited=1)

    docs = {d["id"]: d for d in warehouse_db.get_documents()}
    assert docs[incomplete_doc]["manual_edited"] is True
    assert docs[incomplete_doc]["missing_fields"] == ["Затребував"]


def test_documents_position_count_is_not_filtered_by_accounting(warehouse_db):
    """Колонка «Позицій» показує справжню кількість позицій документа, а не облікову."""
    doc_id = _add_incomplete_photo_doc(warehouse_db)
    for sku in ("SKU-1", "SKU-2", "SKU-3"):
        item_id = warehouse_db.add_item(name=f"Позиція {sku}", sku=sku)
        warehouse_db.add_transaction(
            item_id=item_id, document_id=doc_id, operation_type="income", quantity=5.0
        )

    doc = next(d for d in warehouse_db.get_documents() if d["id"] == doc_id)
    assert doc["transaction_count"] == 3
    assert doc["missing_fields"] == ["Затребував"]


def test_item_transactions_expose_accounting_flag_and_document_data(warehouse_db):
    """Вибірка транзакцій позиції віддає ознаку «враховано» і дані документа для позначок."""
    item_id = warehouse_db.add_item(name="Болт М8", sku="SKU-001", unit="шт")
    complete_doc = _add_complete_photo_doc(warehouse_db)
    incomplete_doc = _add_incomplete_photo_doc(warehouse_db)
    warehouse_db.update_document(complete_doc, manual_edited=1)
    warehouse_db.update_document(incomplete_doc, manual_edited=1)

    warehouse_db.add_transaction(
        item_id=item_id, document_id=complete_doc, operation_type="income", quantity=1.0
    )
    warehouse_db.add_transaction(
        item_id=item_id, document_id=incomplete_doc, operation_type="income", quantity=2.0
    )

    accounted_tx, unaccounted_tx = warehouse_db.get_item_transactions(item_id)
    assert accounted_tx["accounted"] is True
    assert accounted_tx["missing_fields"] == []
    assert accounted_tx["manual_edited"] is True
    assert accounted_tx["document_date"] == "01.08.2026"

    assert unaccounted_tx["accounted"] is False
    assert unaccounted_tx["missing_fields"] == ["Затребував"]
    assert unaccounted_tx["manual_edited"] is True


def test_excel_and_manual_documents_are_always_accounted(warehouse_db):
    """Excel-документ і системний документ ручних коригувань враховуються завжди."""
    item_id = warehouse_db.add_item(name="Світильник 36W", sku="LIGHT-36", unit="шт")
    excel_doc = warehouse_db.add_document(filename="import.xlsx", file_type="excel")
    warehouse_db.add_transaction(
        item_id=item_id, document_id=excel_doc, operation_type="income", quantity=20.0
    )

    warehouse_db.adjust_item_quantity(item_id=item_id, target_quantity=32.0)

    item = next(i for i in warehouse_db.get_items_with_balance() if i["id"] == item_id)
    assert item["total_income"] == 32.0
    assert item["balance"] == 32.0
    assert all(tx["accounted"] for tx in warehouse_db.get_item_transactions(item_id))


def test_migration_adds_manual_edited_to_legacy_db(tmp_path):
    """Міграція додає колонку позначки ручного редагування й не ламає наявні дані."""
    db_path = str(tmp_path / "legacy_flag.db")
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL DEFAULT '',
            uploaded_at REAL NOT NULL,
            doc_number TEXT NOT NULL DEFAULT '',
            doc_date TEXT NOT NULL DEFAULT '',
            raw_text TEXT NOT NULL DEFAULT '',
            doc_type TEXT NOT NULL DEFAULT '',
            requested_by TEXT NOT NULL DEFAULT '',
            requested_via TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE warehouse_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            unit TEXT NOT NULL DEFAULT '',
            supplier TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE warehouse_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL REFERENCES warehouse_items(id),
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            operation_type TEXT NOT NULL CHECK(operation_type IN ('income', 'expense')),
            quantity REAL NOT NULL DEFAULT 0,
            doc_number TEXT NOT NULL DEFAULT '',
            doc_date TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL
        );
    """)
    conn.execute(
        "INSERT INTO documents (filename, file_type, uploaded_at, doc_number, doc_date, doc_type, requested_by, requested_via) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("legacy.jpg", "photo", 1.0, "101", "01.08.2026", "НАКЛАДНА", "комірник", "7939"),
    )
    conn.execute("INSERT INTO warehouse_items (name) VALUES ('Болт М8')")
    conn.execute(
        "INSERT INTO warehouse_transactions (item_id, document_id, operation_type, quantity, created_at) "
        "VALUES (1, 1, 'income', 15.0, 1.0)"
    )
    conn.commit()
    conn.close()

    db = WarehouseDB(db_path=db_path)
    db.init_db()
    try:
        doc = db.get_documents()[0]
        assert doc["manual_edited"] is False
        assert doc["missing_fields"] == []
        item = db.get_items_with_balance()[0]
        assert item["balance"] == 15.0
        assert item["doc_count"] == 1
    finally:
        db.close()


def test_clear_document_transactions_removes_only_that_documents_transactions(warehouse_db):
    """Очищення прибирає транзакції одного документа, не чіпаючи ні інші документи, ні позиції."""
    item_id = warehouse_db.add_item(name="Болт М8", sku="SKU-001", supplier="ТОВ Постач")
    target_doc = _add_complete_photo_doc(warehouse_db)
    other_doc = _add_complete_photo_doc(warehouse_db, filename="nakladna_102.jpg", doc_number="102")
    warehouse_db.add_transaction(
        item_id=item_id, document_id=target_doc, operation_type="income", quantity=5.0
    )
    warehouse_db.add_transaction(
        item_id=item_id, document_id=other_doc, operation_type="income", quantity=3.0
    )

    assert warehouse_db.clear_document_transactions(target_doc) == 1

    assert warehouse_db.get_document_impact(target_doc) == []
    assert len(warehouse_db.get_document_impact(other_doc)) == 1
    assert warehouse_db.get_document(target_doc) is not None
    assert warehouse_db.get_item(item_id)["supplier"] == "ТОВ Постач"


def test_delete_document_still_removes_its_transactions(warehouse_db):
    """Видалення документа й далі прибирає всі його транзакції та сам документ."""
    item_id = warehouse_db.add_item(name="Болт М8", sku="SKU-001")
    doc_id = _add_complete_photo_doc(warehouse_db)
    warehouse_db.add_transaction(
        item_id=item_id, document_id=doc_id, operation_type="income", quantity=5.0
    )

    assert warehouse_db.delete_document(doc_id) is True

    assert warehouse_db.get_document(doc_id) is None
    assert warehouse_db.get_document_impact(doc_id) == []
    remaining = warehouse_db._conn.execute(
        "SELECT COUNT(*) FROM warehouse_transactions WHERE document_id = ?", (doc_id,)
    ).fetchone()[0]
    assert remaining == 0



