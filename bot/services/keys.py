from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.types import BufferedInputFile, Message

from bot.awg.manager import AWGManager, ClientKey
from bot.texts import DOWNLOAD_LINK, key_created, key_done_footer, vpn_import_hint
from bot.utils import make_qr_bytes


async def run_awg(func, telegram_id: int) -> ClientKey:
    return await asyncio.to_thread(func, telegram_id)


async def deliver_key(
    target: Message | Bot,
    result: ClientKey,
    *,
    remint: bool,
    show_footer: bool = True,
    chat_id: int | None = None,
) -> None:
    """Отправить ключ в чат. target — Message или Bot (+ chat_id)."""
    if isinstance(target, Message):
        send = target.answer
        send_photo = target.answer_photo
        send_document = target.answer_document
    else:
        if chat_id is None:
            raise ValueError("chat_id обязателен при передаче Bot")
        send = lambda text, **kw: target.send_message(chat_id, text, **kw)
        send_photo = lambda photo, **kw: target.send_photo(chat_id, photo, **kw)
        send_document = lambda doc, **kw: target.send_document(chat_id, doc, **kw)

    await send(key_created(remint, result.ip))

    qr_bytes = make_qr_bytes(result.vpn_uri)
    await send_photo(
        BufferedInputFile(qr_bytes, filename="amnezia_vpn_qr.png"),
        caption=f"📱 QR-код для {DOWNLOAD_LINK}",
    )

    vpn_file = BufferedInputFile(
        result.vpn_uri.encode("utf-8"),
        filename="amnezia.vpn",
    )
    await send_document(
        vpn_file,
        caption="📄 Ключ AmneziaVPN — откройте файл или вставьте в приложение",
    )

    # Telegram ограничивает длину сообщения; отправляем URI отдельно для копирования
    if len(result.vpn_uri) <= 3900:
        await send(
            f"<b>🔗 Ключ для вставки:</b>\n\n<code>{result.vpn_uri}</code>\n\n{vpn_import_hint()}",
        )

    if show_footer:
        await send(key_done_footer())
