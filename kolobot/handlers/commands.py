"""Command handlers: /start, /help, /status (and later /list, /delete)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from kolobot.messages import HELP_UK, START_UK

if TYPE_CHECKING:
    from kolobot.key_pool import KeyPool

router = Router(name="commands")


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(START_UK)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_UK)


async def cmd_status(
    message: Message,
    *,
    gen_pool: "KeyPool",
    emb_pool: "KeyPool",
) -> None:
    gs = gen_pool.status()
    es = emb_pool.status()
    text = (
        f"<b>Generate pool:</b> {gs['available']}/{gs['total']} available"
        f" (cooldown {gs['cooldown']}, limited {gs['limited']})\n"
        f"<b>Embed pool:</b> {es['available']}/{es['total']} available"
        f" (cooldown {es['cooldown']}, limited {es['limited']})"
    )
    await message.answer(text)
