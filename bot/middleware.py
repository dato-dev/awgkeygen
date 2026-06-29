"""Middleware для логирования входящих событий."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

logger = logging.getLogger("bot.updates")


class UpdateLoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Update):
            self._log_update(event)
        return await handler(event, data)

    def _log_update(self, update: Update) -> None:
        if update.message and update.message.from_user:
            msg = update.message
            user = msg.from_user
            text = (msg.text or msg.caption or "").strip()
            if text.startswith("/"):
                logger.info(
                    "command user_id=%s username=%s text=%s",
                    user.id,
                    user.username,
                    text.split("\n", 1)[0][:120],
                )
            elif text:
                logger.debug(
                    "message user_id=%s username=%s len=%d",
                    user.id,
                    user.username,
                    len(text),
                )
            elif msg.document or msg.photo:
                logger.info(
                    "attachment user_id=%s username=%s type=%s",
                    user.id,
                    user.username,
                    "document" if msg.document else "photo",
                )
        elif update.callback_query and update.callback_query.from_user:
            cb = update.callback_query
            logger.info(
                "callback user_id=%s data=%s",
                cb.from_user.id,
                (cb.data or "")[:80],
            )
