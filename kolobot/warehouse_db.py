"""WarehouseDB: async SQLite wrapper for warehouse inventory management."""

from __future__ import annotations

import datetime
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from kolobot.doc_structurer import extract_requested_by, extract_requested_via

# Обовʼязкові поля бланка: і SQL-умова обліку, і Python-хелпер будуються з цього переліку.
REQUIRED_DOC_FIELDS = (
    ("Тип документу", "doc_type"),
    ("№ документа", "doc_number"),
    ("Дата документа", "doc_date"),
    ("Затребував", "requested_by"),
    ("Через кого", "requested_via"),
)

# Документи, що не проходили розпізнавання: цих полів бланка в них не існує.
NON_OCR_FILE_TYPES = ("excel", "manual")


def missing_doc_fields(doc: Dict[str, Any]) -> List[str]:
    """Назви порожніх обовʼязкових полів документа; для не-OCR документів — порожній список."""
    if (doc.get("file_type") or "") in NON_OCR_FILE_TYPES:
        return []
    return [
        label
        for label, column in REQUIRED_DOC_FIELDS
        if not str(doc.get(column) or "").strip()
    ]


def _accounted_sql(alias: str) -> str:
    """SQL-умова «документ повністю розпізнаний АБО не є OCR-документом»."""
    filled = " AND ".join(
        f"TRIM(COALESCE({alias}.{column}, '')) <> ''"
        for _, column in REQUIRED_DOC_FIELDS
    )
    exempt = ", ".join(f"'{file_type}'" for file_type in NON_OCR_FILE_TYPES)
    return f"({alias}.file_type IN ({exempt}) OR ({filled}))"


class WarehouseDB:

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    def init_db(self) -> None:
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_path TEXT NOT NULL DEFAULT '',
                uploaded_at REAL NOT NULL,
                doc_number TEXT NOT NULL DEFAULT '',
                doc_date TEXT NOT NULL DEFAULT '',
                raw_text TEXT NOT NULL DEFAULT '',
                doc_type TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'completed',
                error_message TEXT NOT NULL DEFAULT '',
                file_id TEXT NOT NULL DEFAULT '',
                chat_id INTEGER NOT NULL DEFAULT 0,
                user_id INTEGER NOT NULL DEFAULT 0,
                requested_by TEXT NOT NULL DEFAULT '',
                requested_via TEXT NOT NULL DEFAULT '',
                manual_edited INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS warehouse_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT '',
                supplier TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                min_balance REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS warehouse_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL REFERENCES warehouse_items(id),
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                operation_type TEXT NOT NULL CHECK(operation_type IN ('income', 'expense')),
                quantity REAL NOT NULL DEFAULT 0,
                doc_number TEXT NOT NULL DEFAULT '',
                doc_date TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL,
                source_row TEXT NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_item ON warehouse_transactions(item_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_doc ON warehouse_transactions(document_id);
            CREATE INDEX IF NOT EXISTS idx_items_sku ON warehouse_items(sku);
        """)
        self._conn.commit()
        self._migrate()

    def _migrate(self) -> None:
        cursor = self._conn.execute("PRAGMA table_info(documents)")
        doc_cols = {row[1] for row in cursor.fetchall()}
        if "doc_type" not in doc_cols:
            self._conn.execute("ALTER TABLE documents ADD COLUMN doc_type TEXT NOT NULL DEFAULT ''")
        if "status" not in doc_cols:
            self._conn.execute("ALTER TABLE documents ADD COLUMN status TEXT NOT NULL DEFAULT 'completed'")
        if "error_message" not in doc_cols:
            self._conn.execute("ALTER TABLE documents ADD COLUMN error_message TEXT NOT NULL DEFAULT ''")
        if "file_id" not in doc_cols:
            self._conn.execute("ALTER TABLE documents ADD COLUMN file_id TEXT NOT NULL DEFAULT ''")
        if "chat_id" not in doc_cols:
            self._conn.execute("ALTER TABLE documents ADD COLUMN chat_id INTEGER NOT NULL DEFAULT 0")
        if "user_id" not in doc_cols:
            self._conn.execute("ALTER TABLE documents ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")
        if "requested_by" not in doc_cols:
            self._conn.execute("ALTER TABLE documents ADD COLUMN requested_by TEXT NOT NULL DEFAULT ''")
        if "requested_via" not in doc_cols:
            self._conn.execute("ALTER TABLE documents ADD COLUMN requested_via TEXT NOT NULL DEFAULT ''")
        if "manual_edited" not in doc_cols:
            self._conn.execute("ALTER TABLE documents ADD COLUMN manual_edited INTEGER NOT NULL DEFAULT 0")
        if "requested_by" not in doc_cols or "requested_via" not in doc_cols:
            self._backfill_requester_fields()

        cursor = self._conn.execute("PRAGMA table_info(warehouse_transactions)")
        tx_cols = {row[1] for row in cursor.fetchall()}
        if "source_row" not in tx_cols:
            self._conn.execute("ALTER TABLE warehouse_transactions ADD COLUMN source_row TEXT NOT NULL DEFAULT ''")

        cursor = self._conn.execute("PRAGMA table_info(warehouse_items)")
        item_cols = {row[1] for row in cursor.fetchall()}
        if "min_balance" not in item_cols:
            self._conn.execute("ALTER TABLE warehouse_items ADD COLUMN min_balance REAL NOT NULL DEFAULT 0")

        self._conn.commit()

    def add_document(
        self,
        filename: str,
        file_type: str,
        file_path: str = "",
        doc_number: str = "",
        doc_date: str = "",
        raw_text: str = "",
        doc_type: str = "",
        status: str = "completed",
        file_id: str = "",
        chat_id: int = 0,
        user_id: int = 0,
        requested_by: str = "",
        requested_via: str = "",
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO documents (filename, file_type, file_path, uploaded_at, doc_number, doc_date, raw_text, doc_type, status, file_id, chat_id, user_id, requested_by, requested_via) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (filename, file_type, file_path, time.time(), doc_number, doc_date, raw_text, doc_type, status, file_id, chat_id, user_id, requested_by, requested_via),
        )
        self._conn.commit()
        return cur.lastrowid

    def _backfill_requester_fields(self) -> None:
        """Одноразово заповнює затребуваного і 'через кого' для документів, збережених до появи колонок."""
        rows = self._conn.execute(
            "SELECT id, raw_text, requested_by, requested_via FROM documents WHERE raw_text != ''"
        ).fetchall()
        for doc_id, raw_text, requested_by, requested_via in rows:
            if requested_by and requested_via:
                continue
            self._conn.execute(
                "UPDATE documents SET requested_by = ?, requested_via = ? WHERE id = ?",
                (
                    requested_by or extract_requested_by(raw_text),
                    requested_via or extract_requested_via(raw_text),
                    doc_id,
                ),
            )

    def add_item(
        self,
        name: str,
        sku: str = "",
        unit: str = "",
        supplier: str = "",
        notes: str = "",
        min_balance: float = 0.0,
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO warehouse_items (sku, name, unit, supplier, notes, min_balance) VALUES (?, ?, ?, ?, ?, ?)",
            (sku, name, unit, supplier, notes, min_balance),
        )
        self._conn.commit()
        return cur.lastrowid

    def find_item(self, sku: str = "", name: str = "") -> Optional[Dict[str, Any]]:
        if sku:
            row = self._conn.execute(
                "SELECT * FROM warehouse_items WHERE sku = ?", (sku,)
            ).fetchone()
            if row:
                return dict(row)
        if name:
            row = self._conn.execute(
                "SELECT * FROM warehouse_items WHERE name = ?", (name,)
            ).fetchone()
            if row:
                return dict(row)
        return None

    def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT * FROM warehouse_items WHERE id = ?", (item_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_or_create_manual_document(self) -> int:
        row = self._conn.execute(
            "SELECT id FROM documents WHERE file_type = 'manual' AND doc_type = 'РУЧНЕ_КОРИГУВАННЯ' ORDER BY id ASC LIMIT 1"
        ).fetchone()
        if row:
            return row["id"]
        return self.add_document(
            filename="Ручне редагування (Користувач)",
            file_type="manual",
            doc_type="РУЧНЕ_КОРИГУВАННЯ",
            raw_text="Системний документ для ручних коригувань позицій та залишків",
        )

    def adjust_item_field(
        self,
        item_id: int,
        field: str,
        new_value: Any,
        comment: str = "",
    ) -> Optional[Dict[str, Any]]:
        field_labels = {
            "name": "Найменування",
            "sku": "Номенклатурний номер",
            "unit": "Од. виміру",
            "supplier": "Постачальник",
            "notes": "Примітки",
            "min_balance": "Мінімальний залишок",
        }
        if field not in field_labels:
            raise ValueError(f"Invalid field: {field}. Allowed: {list(field_labels.keys())}")

        item = self.get_item(item_id)
        if not item:
            return None

        old_value = item.get(field)
        if old_value is None:
            old_value = ""

        if field == "min_balance":
            try:
                new_val_num = float(new_value) if new_value not in (None, "") else 0.0
                if new_val_num < 0:
                    new_val_num = 0.0
            except (ValueError, TypeError):
                new_val_num = 0.0
            new_val_store = new_val_num
            new_val_str = str(int(new_val_num)) if new_val_num == int(new_val_num) else str(new_val_num)
            old_val_str = str(int(old_value)) if isinstance(old_value, (int, float)) and old_value == int(old_value) else str(old_value)
        else:
            new_val_store = str(new_value or "").strip()
            new_val_str = new_val_store
            old_val_str = str(old_value)

        # Update item
        self._conn.execute(
            f"UPDATE warehouse_items SET {field} = ? WHERE id = ?",
            (new_val_store, item_id),
        )
        self._conn.commit()

        # Create zero-quantity audit record
        doc_id = self.get_or_create_manual_document()
        label = field_labels[field]
        source_row = f"Змінено [{label}]: '{old_val_str}' → '{new_val_str}'"
        if comment and comment.strip():
            source_row += f" ({comment.strip()})"

        doc_date = datetime.date.today().strftime("%d.%m.%Y")
        tx_id = self.add_transaction(
            item_id=item_id,
            document_id=doc_id,
            operation_type="income",
            quantity=0.0,
            doc_number="",
            doc_date=doc_date,
            source_row=source_row,
        )

        updated_item = self.get_item(item_id)
        return {
            "success": True,
            "item": updated_item,
            "old_value": old_value,
            "new_value": new_val_store,
            "source_row": source_row,
            "transaction_id": tx_id,
        }

    def get_item_balance(self, item_id: int) -> Optional[float]:
        item = self.get_item(item_id)
        if not item:
            return None
        row = self._conn.execute(f"""
            SELECT
                COALESCE(SUM(CASE WHEN wt.operation_type = 'income' THEN wt.quantity ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN wt.operation_type = 'expense' THEN wt.quantity ELSE 0 END), 0) AS balance
            FROM warehouse_transactions wt
            JOIN documents d ON wt.document_id = d.id
            WHERE wt.item_id = ? AND {_accounted_sql("d")}
        """, (item_id,)).fetchone()
        return float(row["balance"]) if row else 0.0

    def adjust_item_quantity(
        self,
        item_id: int,
        target_quantity: float,
        comment: str = "",
    ) -> Optional[Dict[str, Any]]:
        item = self.get_item(item_id)
        if not item:
            return None

        current_balance = self.get_item_balance(item_id)
        if current_balance is None:
            current_balance = 0.0

        target_qty = float(target_quantity)
        delta = target_qty - current_balance

        def _fmt(val: float) -> str:
            return str(int(val)) if val == int(val) else str(val)

        old_bal_str = _fmt(current_balance)
        target_str = _fmt(target_qty)
        source_row = f"Змінено 'Кількість': {old_bal_str} → {target_str}"
        if comment and comment.strip():
            source_row += f" ({comment.strip()})"

        if abs(delta) < 1e-9:
            return {
                "success": True,
                "item_id": item_id,
                "old_balance": current_balance,
                "target_quantity": target_qty,
                "delta": 0.0,
                "operation_type": None,
                "transaction_id": None,
                "source_row": source_row,
                "item": item,
            }

        operation_type = "income" if delta > 0 else "expense"
        quantity = abs(delta)
        doc_id = self.get_or_create_manual_document()
        doc_date = datetime.date.today().strftime("%d.%m.%Y")

        tx_id = self.add_transaction(
            item_id=item_id,
            document_id=doc_id,
            operation_type=operation_type,
            quantity=quantity,
            doc_number="",
            doc_date=doc_date,
            source_row=source_row,
        )

        return {
            "success": True,
            "item_id": item_id,
            "old_balance": current_balance,
            "target_quantity": target_qty,
            "delta": delta,
            "operation_type": operation_type,
            "transaction_id": tx_id,
            "source_row": source_row,
            "item": item,
        }

    def update_item(self, item_id: int, **kwargs: Any) -> None:
        allowed = {"sku", "name", "unit", "supplier", "notes", "min_balance"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [item_id]
        self._conn.execute(
            f"UPDATE warehouse_items SET {set_clause} WHERE id = ?", values
        )
        self._conn.commit()

    def add_transaction(
        self,
        item_id: int,
        document_id: int,
        operation_type: str,
        quantity: float,
        doc_number: str = "",
        doc_date: str = "",
        source_row: str = "",
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO warehouse_transactions (item_id, document_id, operation_type, quantity, doc_number, doc_date, created_at, source_row) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (item_id, document_id, operation_type, quantity, doc_number, doc_date, time.time(), source_row),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_items_with_balance(self) -> List[Dict[str, Any]]:
        accounted = _accounted_sql("d")
        rows = self._conn.execute(f"""
            SELECT
                wi.id, wi.sku, wi.name, wi.unit, wi.supplier, wi.notes, wi.min_balance,
                COALESCE(SUM(CASE WHEN wt.operation_type = 'income' AND {accounted} THEN wt.quantity ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN wt.operation_type = 'expense' AND {accounted} THEN wt.quantity ELSE 0 END), 0) AS total_expense,
                MAX(CASE WHEN {accounted} THEN wt.doc_date END) AS last_doc_date,
                MAX(CASE WHEN {accounted} THEN wt.doc_number END) AS last_doc_number,
                COUNT(DISTINCT CASE WHEN d.file_type != 'manual' AND {accounted} THEN wt.document_id END) AS doc_count
            FROM warehouse_items wi
            LEFT JOIN warehouse_transactions wt ON wi.id = wt.item_id
            LEFT JOIN documents d ON wt.document_id = d.id
            GROUP BY wi.id
            ORDER BY wi.name
        """).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["balance"] = d["total_income"] - d["total_expense"]
            result.append(d)
        return result

    def get_item_transactions(self, item_id: int) -> List[Dict[str, Any]]:
        rows = self._conn.execute(f"""
            SELECT
                wt.id, wt.operation_type, wt.quantity, wt.doc_number, wt.doc_date, wt.created_at,
                wt.source_row,
                d.id AS document_id, d.filename, d.file_type, d.file_path, d.doc_type,
                d.requested_by, d.requested_via, d.manual_edited,
                d.doc_number AS document_number, d.doc_date AS document_date,
                CASE WHEN {_accounted_sql("d")} THEN 1 ELSE 0 END AS accounted
            FROM warehouse_transactions wt
            JOIN documents d ON wt.document_id = d.id
            WHERE wt.item_id = ?
            ORDER BY wt.created_at ASC
        """, (item_id,)).fetchall()
        result = []
        running_balance = 0.0
        for r in rows:
            d = dict(r)
            d["accounted"] = bool(d["accounted"])
            d["manual_edited"] = bool(d["manual_edited"])
            d["missing_fields"] = missing_doc_fields({
                "file_type": d["file_type"],
                "doc_type": d["doc_type"],
                "doc_number": d["document_number"],
                "doc_date": d["document_date"],
                "requested_by": d["requested_by"],
                "requested_via": d["requested_via"],
            })
            # Накопичувальний залишок рахує лише враховані рядки, щоб збігатися із залишком позиції.
            if d["accounted"]:
                if d["operation_type"] == "income":
                    running_balance += d["quantity"]
                else:
                    running_balance -= d["quantity"]
            d["running_balance"] = running_balance
            result.append(d)
        return result

    def get_documents(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute("""
            SELECT
                d.id, d.filename, d.file_type, d.file_path, d.uploaded_at,
                d.doc_number, d.doc_date, d.doc_type, d.raw_text,
                d.status, d.error_message, d.requested_by, d.requested_via, d.manual_edited,
                COUNT(wt.id) AS transaction_count
            FROM documents d
            LEFT JOIN warehouse_transactions wt ON d.id = wt.document_id
            GROUP BY d.id
            ORDER BY d.uploaded_at DESC
        """).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["manual_edited"] = bool(d["manual_edited"])
            d["missing_fields"] = missing_doc_fields(d)
            result.append(d)
        return result

    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_unprocessed_documents(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute("""
            SELECT * FROM documents
            WHERE status IN ('queued', 'processing_ocr', 'processing_emb')
            ORDER BY id ASC
        """).fetchall()
        return [dict(r) for r in rows]

    def update_document(self, doc_id: int, **kwargs: Any) -> bool:
        allowed = {
            "filename", "file_type", "file_path", "doc_number",
            "doc_date", "raw_text", "doc_type", "status", "error_message",
            "file_id", "chat_id", "user_id", "requested_by", "requested_via",
            "manual_edited",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        row = self._conn.execute(
            "SELECT id FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if not row:
            return False
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [doc_id]
            self._conn.execute(
                f"UPDATE documents SET {set_clause} WHERE id = ?", values
            )
            self._conn.commit()
        return True

    def get_document_impact(self, doc_id: int) -> List[Dict[str, Any]]:
        rows = self._conn.execute("""
            SELECT
                wt.id AS transaction_id, wt.operation_type, wt.quantity,
                wt.doc_number, wt.doc_date, wt.source_row,
                wi.id AS item_id, wi.sku, wi.name, wi.unit
            FROM warehouse_transactions wt
            JOIN warehouse_items wi ON wt.item_id = wi.id
            WHERE wt.document_id = ?
            ORDER BY wi.name
        """, (doc_id,)).fetchall()
        return [dict(r) for r in rows]

    def clear_document_transactions(self, doc_id: int) -> int:
        """Прибирає всі транзакції документа, не чіпаючи позиції складу та їхні ручні поля.

        Повертає кількість видалених рядків. Запис не комітиться — його завершує
        викликач, щоб очищення й оновлення полів документа лягли в одну операцію запису.
        """
        cur = self._conn.execute(
            "DELETE FROM warehouse_transactions WHERE document_id = ?", (doc_id,)
        )
        return cur.rowcount

    def delete_document(self, doc_id: int) -> bool:
        row = self._conn.execute(
            "SELECT id FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if not row:
            return False
        self.clear_document_transactions(doc_id)
        self._conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self._cleanup_orphan_items()
        self._conn.commit()
        return True

    def _cleanup_orphan_items(self) -> None:
        self._conn.execute("""
            DELETE FROM warehouse_items
            WHERE id NOT IN (SELECT DISTINCT item_id FROM warehouse_transactions)
        """)
