"""WarehouseDB: async SQLite wrapper for warehouse inventory management."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


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
                doc_type TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS warehouse_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT '',
                supplier TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT ''
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

        cursor = self._conn.execute("PRAGMA table_info(warehouse_transactions)")
        tx_cols = {row[1] for row in cursor.fetchall()}
        if "source_row" not in tx_cols:
            self._conn.execute("ALTER TABLE warehouse_transactions ADD COLUMN source_row TEXT NOT NULL DEFAULT ''")

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
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO documents (filename, file_type, file_path, uploaded_at, doc_number, doc_date, raw_text, doc_type) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (filename, file_type, file_path, time.time(), doc_number, doc_date, raw_text, doc_type),
        )
        self._conn.commit()
        return cur.lastrowid

    def add_item(
        self,
        name: str,
        sku: str = "",
        unit: str = "",
        supplier: str = "",
        notes: str = "",
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO warehouse_items (sku, name, unit, supplier, notes) VALUES (?, ?, ?, ?, ?)",
            (sku, name, unit, supplier, notes),
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

    def update_item(self, item_id: int, **kwargs: Any) -> None:
        allowed = {"sku", "name", "unit", "supplier", "notes"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v}
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
        rows = self._conn.execute("""
            SELECT
                wi.id, wi.sku, wi.name, wi.unit, wi.supplier, wi.notes,
                COALESCE(SUM(CASE WHEN wt.operation_type = 'income' THEN wt.quantity ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN wt.operation_type = 'expense' THEN wt.quantity ELSE 0 END), 0) AS total_expense,
                MAX(wt.doc_date) AS last_doc_date,
                MAX(wt.doc_number) AS last_doc_number
            FROM warehouse_items wi
            LEFT JOIN warehouse_transactions wt ON wi.id = wt.item_id
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
        rows = self._conn.execute("""
            SELECT
                wt.id, wt.operation_type, wt.quantity, wt.doc_number, wt.doc_date, wt.created_at,
                wt.source_row,
                d.id AS document_id, d.filename, d.file_type, d.file_path, d.doc_type
            FROM warehouse_transactions wt
            JOIN documents d ON wt.document_id = d.id
            WHERE wt.item_id = ?
            ORDER BY wt.created_at ASC
        """, (item_id,)).fetchall()
        result = []
        running_balance = 0.0
        for r in rows:
            d = dict(r)
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
                d.doc_number, d.doc_date, d.doc_type,
                COUNT(wt.id) AS transaction_count
            FROM documents d
            LEFT JOIN warehouse_transactions wt ON d.id = wt.document_id
            GROUP BY d.id
            ORDER BY d.uploaded_at DESC
        """).fetchall()
        return [dict(r) for r in rows]

    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        return dict(row) if row else None

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

    def delete_document(self, doc_id: int) -> bool:
        row = self._conn.execute(
            "SELECT id FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if not row:
            return False
        self._conn.execute(
            "DELETE FROM warehouse_transactions WHERE document_id = ?", (doc_id,)
        )
        self._conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self._cleanup_orphan_items()
        self._conn.commit()
        return True

    def _cleanup_orphan_items(self) -> None:
        self._conn.execute("""
            DELETE FROM warehouse_items
            WHERE id NOT IN (SELECT DISTINCT item_id FROM warehouse_transactions)
        """)
