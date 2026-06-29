from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.types import BufferedInputFile, Message

from bot.awg.manager import ClientKey
from bot.keyboards import vpn_copy_keyboard
from bot.texts import key_created, key_done_footer, key_vpn_text


async def run_awg(func, /, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


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
