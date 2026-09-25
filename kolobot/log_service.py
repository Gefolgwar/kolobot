"""In-memory logging buffer and handler for web console and real-time event streaming."""

from __future__ import annotations

import asyncio
import collections
import datetime
import logging
import threading
from dataclasses import asdict, dataclass
from typing import Any, List, Optional, Set

_MAX_BUFFER_SIZE = 5000


@dataclass
class LogEntry:
    id: int
    timestamp: str
    level: str  # 'INFO', 'SUCCESS', 'WARN', 'ERR', 'DEBUG'
    logger: str
    message: str
    raw: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_log_level(level_name: str) -> str:
    """Normalize python log level names to UI categories: INFO, SUCCESS, WARN, ERR, DEBUG."""
    lvl = (level_name or "").upper().strip()
    if lvl in ("CRITICAL", "ERROR", "ERR", "FATAL"):
        return "ERR"
    if lvl in ("WARNING", "WARN"):
        return "WARN"
    if lvl in ("SUCCESS",):
        return "SUCCESS"
    if lvl in ("DEBUG",):
        return "DEBUG"
    return "INFO"


class LogBuffer:
    """Thread-safe circular log buffer with optional async listeners."""

    def __init__(self, maxlen: int = _MAX_BUFFER_SIZE) -> None:
        self._maxlen = maxlen
        self._buffer: collections.deque[LogEntry] = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._seq = 0
        self._total_collected = 0
        self._subscribers: Set[asyncio.Queue[LogEntry]] = set()

    def add_entry(
        self,
        level: str,
        logger_name: str,
        message: str,
        timestamp: Optional[str] = None,
        raw: Optional[str] = None,
    ) -> LogEntry:
        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        norm_level = normalize_log_level(level)
        if raw is None:
            raw = f"{timestamp} [{norm_level}] {logger_name}: {message}"

        with self._lock:
            self._seq += 1
            self._total_collected += 1
            entry = LogEntry(
                id=self._seq,
                timestamp=timestamp,
                level=norm_level,
                logger=logger_name,
                message=message,
                raw=raw,
            )
            self._buffer.append(entry)

        # Notify async subscribers safely
        if self._subscribers:
            for q in list(self._subscribers):
                try:
                    q.put_nowait(entry)
                except Exception:
                    pass

        return entry

    def get_logs(
        self,
        since_id: int = 0,
        limit: int = 500,
        level: Optional[str] = None,
        query: Optional[str] = None,
    ) -> tuple[List[LogEntry], int, int]:
        """
        Returns (logs, total_count, last_id).
        total_count is total logs currently in buffer.
        """
        with self._lock:
            entries = list(self._buffer)
            total = len(entries)
            last_id = self._seq

        if since_id > 0:
            entries = [e for e in entries if e.id > since_id]

        if level:
            target_level = normalize_log_level(level)
            entries = [e for e in entries if e.level == target_level]

        if query:
            q_lower = query.lower()
            entries = [
                e for e in entries
                if q_lower in e.message.lower()
                or q_lower in e.logger.lower()
                or q_lower in e.raw.lower()
            ]

        if limit > 0 and len(entries) > limit:
            entries = entries[-limit:]

        return entries, total, last_id

    def clear(self) -> int:
        """Clears the buffer and returns number of cleared entries."""
        with self._lock:
            count = len(self._buffer)
            self._buffer.clear()
            return count

    def get_total_count(self) -> int:
        with self._lock:
            return len(self._buffer)

    def subscribe(self) -> asyncio.Queue[LogEntry]:
        q: asyncio.Queue[LogEntry] = asyncio.Queue(maxsize=1000)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[LogEntry]) -> None:
        self._subscribers.discard(q)


class InMemoryLogHandler(logging.Handler):
    """Logging handler that formats records and pushes them into LogBuffer."""

    def __init__(self, log_buffer: LogBuffer) -> None:
        super().__init__()
        self.log_buffer = log_buffer
        self.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            # Format exception details if present
            exc_text = ""
            if record.exc_info:
                if not record.exc_text:
                    record.exc_text = self.formatter.formatException(record.exc_info)
                if record.exc_text:
                    exc_text = "\n" + record.exc_text

            full_msg = record.getMessage() + exc_text
            created_dt = datetime.datetime.fromtimestamp(record.created)
            ts_str = created_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            # Detect success in message or logger
            level = record.levelname
            if "success" in full_msg.lower() or "завершено успішно" in full_msg.lower():
                if level == "INFO":
                    level = "SUCCESS"

            self.log_buffer.add_entry(
                level=level,
                logger_name=record.name,
                message=full_msg,
                timestamp=ts_str,
                raw=msg,
            )
        except Exception:
            self.handleError(record)


# Global singleton instance
_GLOBAL_LOG_BUFFER = LogBuffer()
_GLOBAL_HANDLER: Optional[InMemoryLogHandler] = None


def get_global_log_buffer() -> LogBuffer:
    return _GLOBAL_LOG_BUFFER


def setup_logging_capture(
    root_logger: Optional[logging.Logger] = None,
    buffer: Optional[LogBuffer] = None,
    level: int = logging.INFO,
) -> InMemoryLogHandler:
    """Attach the in-memory log handler to the specified or root logger."""
    global _GLOBAL_HANDLER
    target_logger = root_logger or logging.getLogger()
    target_buffer = buffer or _GLOBAL_LOG_BUFFER

    if _GLOBAL_HANDLER is None:
        _GLOBAL_HANDLER = InMemoryLogHandler(log_buffer=target_buffer)
        _GLOBAL_HANDLER.setLevel(level)

    if _GLOBAL_HANDLER not in target_logger.handlers:
        target_logger.addHandler(_GLOBAL_HANDLER)

    return _GLOBAL_HANDLER
