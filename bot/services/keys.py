from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.types import BufferedInputFile, Message

from bot.awg.manager import AWGManager, ClientKey
from bot.database import Database, User
from bot.keyboards import vpn_copy_keyboard
from bot.texts import key_created, key_done_footer, key_vpn_text

logger = logging.getLogger(__name__)


async def run_awg(func, /, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


async def sync_peer_state(db: Database, awg: AWGManager, user: User) -> bool:
    """Сверить флаг ключа в БД с конфигом сервера. Возвращает реальное состояние.

    Источник истины — сервер: БД могла разойтись с ним после переноса бота на
    другой сервер или ручной правки awg0.conf. Поле user.has_key обновляется
    на месте, чтобы вызывающий код видел актуальное значение.
    """
    exists = await run_awg(awg.peer_exists, user.telegram_id)
    if exists != user.has_key:
        logger.warning(
            "Флаг ключа для %s разошёлся с сервером (БД=%s, сервер=%s) — синхронизирую",
            user.telegram_id, user.has_key, exists,
        )
        await db.set_has_key(user.telegram_id, exists)
        user.has_key = exists
    return exists


async def deliver_key(
    target: Message | Bot,
    result: ClientKey,
    *,
    remint: bool,
    show_header: bool = True,
    show_footer: bool = True,
    chat_id: int | None = None,
) -> None:
    """Отправить ключ в чат. target — Message или Bot (+ chat_id)."""
    if isinstance(target, Message):
        send = target.answer
        send_document = target.answer_document
    else:
        if chat_id is None:
            raise ValueError("chat_id обязателен при передаче Bot")
        send = lambda text, **kw: target.send_message(chat_id, text, **kw)
        send_document = lambda doc, **kw: target.send_document(chat_id, doc, **kw)

    copy_kb = vpn_copy_keyboard(result.vpn_uri)

    if show_header:
        await send(key_created(remint, result.ip))

    vpn_text = key_vpn_text(result.vpn_uri)
    if vpn_text:
        await send(vpn_text, reply_markup=copy_kb)
    else:
        await send(
            "⚠️ Ключ слишком длинный для сообщения — используйте файл <code>.vpn</code> ниже",
        )

    vpn_file = BufferedInputFile(
        result.vpn_uri.encode("utf-8"),
        filename="amnezia.vpn",
    )
    await send_document(
        vpn_file,
        caption="📄 Файл <code>amnezia.vpn</code> — альтернативный способ импорта",
    )

    if show_footer:
        await send(key_done_footer())
