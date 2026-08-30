"""Command handler copy for /start and /help."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from kolobot.handlers.commands import cmd_clear, cmd_help, cmd_start
from kolobot.messages import HELP_UK, START_UK
from kolobot.queue_service import ClearResult


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


@pytest.mark.asyncio
async def test_cmd_clear_returns_itemized_summary():
    message = MagicMock()
    message.answer = AsyncMock()

    mock_queue_service = MagicMock()
    mock_queue_service.clear = AsyncMock(
        return_value=ClearResult(
            cancelled_active=1,
            drained_queue=2,
            cleared_cards=3,
            deleted_files=6,
        )
    )

    await cmd_clear(message, queue_service=mock_queue_service)

    mock_queue_service.clear.assert_awaited_once()
    message.answer.assert_awaited_once()
    text = message.answer.await_args.args[0]

    assert "Чергу та активні завдання очищено" in text
    assert "Скасовано активних задач: 1" in text
    assert "Очищено документів з черги: 2" in text
    assert "Видалено незбережених карток: 3" in text
    assert "Видалено тимчасових файлів: 6" in text

