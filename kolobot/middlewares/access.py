"""Centralized personal allowlist gate."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from kolobot.messages import ACCESS_DENIED_UK


class AccessMiddleware(BaseMiddleware):
    """Allow only OWNER_USER_ID; polite Ukrainian reject otherwise."""

    def __init__(self, owner_user_id: int) -> None:
        self.owner_user_id = owner_user_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        user_id = getattr(user, "id", None) if user is not None else None
        if user_id != self.owner_user_id:
            answer = getattr(event, "answer", None)
            if callable(answer):
                await answer(ACCESS_DENIED_UK)
            return None
        return await handler(event, data)
