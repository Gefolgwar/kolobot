"""Hardening: confirm timeout, quota wait-then-sorry."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional


class RetryableAPIError(RuntimeError):
    """Transient API error (429/503) that should be retried."""


class ConfirmTimeoutChecker:
    """Check if pending confirm has exceeded timeout."""

    def __init__(
        self,
        timeout_sec: int = 600,
        time_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        self._timeout = timeout_sec
        self._time = time_fn or time.time
        self._started_at: Optional[float] = None

    def mark_pending(self, started_at: Optional[float] = None) -> None:
        self._started_at = started_at if started_at is not None else self._time()

    def clear(self) -> None:
        self._started_at = None

    def is_expired(self) -> bool:
        if self._started_at is None:
            return False
        return self._time() - self._started_at > self._timeout


@dataclass
class QuotaResult:
    exhausted: bool = False
    value: Any = None
    message: str = ""


class QuotaHandler:
    """Wrap pool-backed calls with short wait/retry then Ukrainian sorry."""

    async def with_retry(
        self,
        fn: Callable[..., Awaitable[Any]],
        max_wait: float = 5.0,
        poll: float = 0.5,
    ) -> QuotaResult:
        from kolobot.key_pool import KeyPoolExhausted

        deadline = time.time() + max_wait
        while True:
            try:
                result = await fn()
                return QuotaResult(value=result)
            except (KeyPoolExhausted, RetryableAPIError):
                if time.time() >= deadline:
                    return QuotaResult(
                        exhausted=True,
                        message="Усі ключі зайняті — спробуй пізніше.",
                    )
                await asyncio.sleep(min(poll, max(0, deadline - time.time())))
