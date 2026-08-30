"""/status shows pool availability without exposing secrets."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from kolobot.handlers.commands import cmd_status


@pytest.mark.asyncio
async def test_status_shows_pool_counts_no_secrets():
    message = MagicMock()
    message.answer = AsyncMock()

    gen_pool = MagicMock()
    gen_pool.status.return_value = {
        "kind": "generate",
        "total": 3,
        "available": 2,
        "cooldown": 1,
        "in_flight": 0,
        "limited": 0,
    }
    emb_pool = MagicMock()
    emb_pool.status.return_value = {
        "kind": "embed",
        "total": 2,
        "available": 2,
        "cooldown": 0,
        "in_flight": 0,
        "limited": 0,
    }

    await cmd_status(message, gen_pool=gen_pool, emb_pool=emb_pool)

    message.answer.assert_awaited_once()
    text = message.answer.await_args.args[0]
    assert "generate" in text.lower() or "генер" in text.lower()
    assert "embed" in text.lower() or "ембед" in text.lower()
    assert "2" in text and "3" in text
    assert "secret" not in text.lower()
    assert "key-" not in text.lower()
