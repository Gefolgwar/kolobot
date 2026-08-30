"""Unit tests for LogBuffer, InMemoryLogHandler, and log capture service."""

from __future__ import annotations

import asyncio
import logging
import pytest

from kolobot.log_service import (
    LogBuffer,
    LogEntry,
    InMemoryLogHandler,
    normalize_log_level,
    setup_logging_capture,
)


def test_normalize_log_level():
    assert normalize_log_level("INFO") == "INFO"
    assert normalize_log_level("WARNING") == "WARN"
    assert normalize_log_level("WARN") == "WARN"
    assert normalize_log_level("ERROR") == "ERR"
    assert normalize_log_level("CRITICAL") == "ERR"
    assert normalize_log_level("FATAL") == "ERR"
    assert normalize_log_level("SUCCESS") == "SUCCESS"
    assert normalize_log_level("DEBUG") == "DEBUG"
    assert normalize_log_level("unknown") == "INFO"


def test_log_buffer_add_and_get():
    buf = LogBuffer(maxlen=10)
    e1 = buf.add_entry(level="INFO", logger_name="test.mod", message="System started")
    assert e1.id == 1
    assert e1.level == "INFO"
    assert e1.logger == "test.mod"
    assert e1.message == "System started"

    e2 = buf.add_entry(level="WARN", logger_name="test.db", message="Slow query detected")
    assert e2.id == 2
    assert e2.level == "WARN"

    e3 = buf.add_entry(level="ERROR", logger_name="test.net", message="Connection failed")
    assert e3.id == 3
    assert e3.level == "ERR"

    logs, total, last_id = buf.get_logs()
    assert total == 3
    assert last_id == 3
    assert len(logs) == 3


def test_log_buffer_since_id():
    buf = LogBuffer(maxlen=10)
    for i in range(5):
        buf.add_entry(level="INFO", logger_name="test", message=f"msg {i+1}")

    logs, total, last_id = buf.get_logs(since_id=3)
    assert total == 5
    assert last_id == 5
    assert len(logs) == 2
    assert logs[0].id == 4
    assert logs[1].id == 5


def test_log_buffer_filter_level():
    buf = LogBuffer(maxlen=10)
    buf.add_entry(level="INFO", logger_name="app", message="info msg")
    buf.add_entry(level="WARN", logger_name="app", message="warn msg")
    buf.add_entry(level="ERROR", logger_name="app", message="err msg")

    logs, _, _ = buf.get_logs(level="WARN")
    assert len(logs) == 1
    assert logs[0].level == "WARN"

    logs_err, _, _ = buf.get_logs(level="ERROR")
    assert len(logs_err) == 1
    assert logs_err[0].level == "ERR"


def test_log_buffer_filter_query():
    buf = LogBuffer(maxlen=10)
    buf.add_entry(level="INFO", logger_name="kolobot.db", message="Loaded 42 items")
    buf.add_entry(level="INFO", logger_name="kolobot.ocr", message="OCR processing document.pdf")
    buf.add_entry(level="ERR", logger_name="kolobot.gateway", message="Gemini 429 quota reached")

    logs, _, _ = buf.get_logs(query="ocr")
    assert len(logs) == 1
    assert "OCR" in logs[0].message

    logs_db, _, _ = buf.get_logs(query="kolobot.db")
    assert len(logs_db) == 1
    assert logs_db[0].logger == "kolobot.db"


def test_log_buffer_clear():
    buf = LogBuffer(maxlen=10)
    buf.add_entry(level="INFO", logger_name="app", message="m1")
    buf.add_entry(level="INFO", logger_name="app", message="m2")
    assert buf.get_total_count() == 2

    cleared = buf.clear()
    assert cleared == 2
    assert buf.get_total_count() == 0
    logs, total, _ = buf.get_logs()
    assert len(logs) == 0
    assert total == 0


def test_in_memory_log_handler_emit():
    buf = LogBuffer(maxlen=100)
    handler = InMemoryLogHandler(log_buffer=buf)

    test_logger = logging.getLogger("test_capture_logger")
    test_logger.setLevel(logging.INFO)
    test_logger.addHandler(handler)

    test_logger.info("Operation finished successfully")
    test_logger.warning("Low disk space")
    try:
        raise ValueError("Something broke")
    except Exception:
        test_logger.error("Failed to process", exc_info=True)

    logs, total, _ = buf.get_logs()
    assert total == 3
    assert logs[0].level == "SUCCESS"  # auto-detected from 'successfully'
    assert logs[1].level == "WARN"
    assert logs[2].level == "ERR"
    assert "ValueError: Something broke" in logs[2].message


@pytest.mark.asyncio
async def test_log_buffer_subscribers():
    buf = LogBuffer(maxlen=10)
    q = buf.subscribe()
    try:
        buf.add_entry(level="INFO", logger_name="test", message="async event")
        entry = await asyncio.wait_for(q.get(), timeout=1.0)
        assert entry.message == "async event"
    finally:
        buf.unsubscribe(q)
