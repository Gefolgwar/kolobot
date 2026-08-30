"""Hardening: confirm timeout helper, tmp GC on boot, quota wait-then-sorry."""

from __future__ import annotations

import os
import time

import pytest
from unittest.mock import AsyncMock, MagicMock

from kolobot.hardening import ConfirmTimeoutChecker, QuotaHandler


class FakeClock:
    def __init__(self, t: float = 1000.0):
        self.t = t

    def time(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


def test_confirm_not_expired_within_timeout():
    clock = FakeClock(1000)
    checker = ConfirmTimeoutChecker(timeout_sec=600, time_fn=clock.time)
    checker.mark_pending(started_at=1000.0)
    clock.advance(300)
    assert not checker.is_expired()


def test_confirm_expired_after_timeout():
    clock = FakeClock(1000)
    checker = ConfirmTimeoutChecker(timeout_sec=600, time_fn=clock.time)
    checker.mark_pending(started_at=1000.0)
    clock.advance(601)
    assert checker.is_expired()


def test_confirm_not_expired_when_no_pending():
    clock = FakeClock(1000)
    checker = ConfirmTimeoutChecker(timeout_sec=600, time_fn=clock.time)
    assert not checker.is_expired()


def test_clear_pending_resets():
    clock = FakeClock(1000)
    checker = ConfirmTimeoutChecker(timeout_sec=600, time_fn=clock.time)
    checker.mark_pending(started_at=1000.0)
    checker.clear()
    clock.advance(700)
    assert not checker.is_expired()


def test_gc_tmp_on_boot_clears_only_tmp(tmp_path):
    from kolobot.file_store import FileStore
    fs = FileStore(downloads_path=str(tmp_path))
    # Create tmp and final files
    tmp_file = fs.save_tmp(b"tmp-data", ext=".jpg")
    final = tmp_path / "keep.jpg"
    final.write_bytes(b"final-data")

    fs.gc_tmp()

    assert not os.path.exists(tmp_file)
    assert os.path.isfile(str(final))


@pytest.mark.asyncio
async def test_quota_handler_returns_sorry_on_exhaustion():
    from kolobot.key_pool import KeyPoolExhausted
    handler = QuotaHandler()
    result = await handler.with_retry(
        fn=AsyncMock(side_effect=KeyPoolExhausted("no keys")),
        max_wait=0.0,
    )
    assert result.exhausted
    assert "спробуй" in result.message.lower() or "пізніше" in result.message.lower()


@pytest.mark.asyncio
async def test_quota_handler_passes_through_on_success():
    handler = QuotaHandler()
    fn = AsyncMock(return_value="ok-result")
    result = await handler.with_retry(fn=fn, max_wait=0.0)
    assert not result.exhausted
    assert result.value == "ok-result"
