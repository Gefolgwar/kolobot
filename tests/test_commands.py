"""Command handler copy for /start and /help."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from kolobot.handlers.commands import cmd_help, cmd_start
from kolobot.messages import HELP_UK, START_UK


@pytest.mark.asyncio
async def test_start_confirms_readiness_in_ukrainian():
    message = MagicMock()
    message.answer = AsyncMock()

    await cmd_start(message)

    message.answer.assert_awaited_once()
    text = message.answer.await_args.args[0]
    assert text == START_UK
    assert "особистий" in text.lower() or "архів" in text.lower()


@pytest.mark.asyncio
async def test_help_documents_phase1_limits():
    message = MagicMock()
    message.answer = AsyncMock()

    await cmd_help(message)

    message.answer.assert_awaited_once_with(HELP_UK)
    text = HELP_UK.lower()
    assert "зображ" in text
    assert "одне" in text or "один" in text
