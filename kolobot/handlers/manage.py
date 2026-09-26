"""/status, /list, /delete, /clear, and the delete-confirmation buttons."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from kolobot.handlers.commands import cmd_clear, cmd_status
from kolobot.handlers.context import AppContext


def register(router: Router, ctx: AppContext) -> None:
    """Put the management commands on ``router``."""

    @router.message(Command("status"))
    async def _status(message: Message):
        await cmd_status(
            message,
            gen_pool=ctx.gen_pool,
            emb_pool=ctx.emb_pool,
            queue_service=ctx.queue_service,
        )

    @router.message(Command("list"))
    async def _list(message: Message):
        await ctx.list_delete.handle_list(message, user_id=ctx.owner_user_id)

    @router.message(Command("delete"))
    async def _delete(message: Message):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Використання: /delete <id>")
            return
        result = await ctx.list_delete.delete_doc(
            doc_id=parts[1].strip(), user_id=ctx.owner_user_id
        )
        if result.success:
            await message.answer("Документ видалено.")
        else:
            await message.answer(result.error or "Помилка видалення.")

    @router.message(Command("clear"))
    async def _clear(message: Message):
        await cmd_clear(message, queue_service=ctx.queue_service)

    @router.callback_query(F.data.startswith("del_yes:"))
    async def _del_confirm(callback: CallbackQuery):
        doc_id = callback.data.split(":", 1)[1]
        result = await ctx.list_delete.delete_doc(
            doc_id=doc_id, user_id=ctx.owner_user_id
        )
        if callback.message:
            if result.success:
                await callback.message.answer("Видалено.")
            else:
                await callback.message.answer(result.error or "Помилка.")
        await callback.answer()

    @router.callback_query(F.data == "del_no")
    async def _del_cancel(callback: CallbackQuery):
        if callback.message:
            await callback.message.answer("Скасовано.")
        await callback.answer()
