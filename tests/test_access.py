"""Access gate: only OWNER_USER_ID proceeds; others get polite Ukrainian reject."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from kolobot.middlewares.access import AccessMiddleware
from kolobot.messages import ACCESS_DENIED_UK


@pytest.mark.asyncio
async def test_non_owner_is_rejected_and_handler_not_called():
    middleware = AccessMiddleware(owner_user_id=100)
    handler = AsyncMock(return_value="ok")
    event = SimpleNamespace(
        from_user=SimpleNamespace(id=999),
        answer=AsyncMock(),
    )
    data: dict = {}

    result = await middleware(handler, event, data)

    assert result is None
    handler.assert_not_awaited()
    event.answer.assert_awaited_once()
    assert ACCESS_DENIED_UK in event.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_owner_reaches_handler():
    middleware = AccessMiddleware(owner_user_id=100)
    handler = AsyncMock(return_value="ok")
    event = SimpleNamespace(
        from_user=SimpleNamespace(id=100),
        answer=AsyncMock(),
    )
    data: dict = {}

    result = await middleware(handler, event, data)

    assert result == "ok"
    handler.assert_awaited_once()
    event.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_user_is_rejected_silently():
    middleware = AccessMiddleware(owner_user_id=100)
    handler = AsyncMock(return_value="ok")
    event = SimpleNamespace(from_user=None, answer=AsyncMock())
    data: dict = {}

    result = await middleware(handler, event, data)

    assert result is None
    handler.assert_not_awaited()
