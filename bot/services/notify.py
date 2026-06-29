"""Массовая рассылка уведомлений одобренным пользователям."""

from __future__ import annotations

import asyncio
import html
import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import Message

from bot.database import User

logger = logging.getLogger(__name__)

CAPTION_LIMIT = 1024


@dataclass(frozen=True)
class MediaAttachment:
    kind: str
    file_id: str


def format_broadcast(text: str) -> str:
    safe = html.escape(text)
    return (
        "📢 <b>Уведомление</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{safe}"
    )


def extract_media(message: Message) -> MediaAttachment | None:
    if message.document:
        return MediaAttachment("document", message.document.file_id)
    if message.photo:
        return MediaAttachment("photo", message.photo[-1].file_id)
    if message.video:
        return MediaAttachment("video", message.video.file_id)
    if message.audio:
        return MediaAttachment("audio", message.audio.file_id)
    if message.voice:
        return MediaAttachment("voice", message.voice.file_id)
    if message.animation:
        return MediaAttachment("animation", message.animation.file_id)
    if message.video_note:
        return MediaAttachment("video_note", message.video_note.file_id)
    return None


def resolve_media_source(message: Message) -> Message | None:
    if extract_media(message):
        return message
    reply = message.reply_to_message
    if reply and extract_media(reply):
        return reply
    return None


async def _send_media(
    bot: Bot,
    chat_id: int,
    media: MediaAttachment,
    caption: str | None,
) -> None:
    kwargs: dict = {}
    if caption:
        kwargs["caption"] = caption
        kwargs["parse_mode"] = ParseMode.HTML

    if media.kind == "document":
        await bot.send_document(chat_id, media.file_id, **kwargs)
    elif media.kind == "photo":
        await bot.send_photo(chat_id, media.file_id, **kwargs)
    elif media.kind == "video":
        await bot.send_video(chat_id, media.file_id, **kwargs)
    elif media.kind == "audio":
        await bot.send_audio(chat_id, media.file_id, **kwargs)
    elif media.kind == "voice":
        await bot.send_voice(chat_id, media.file_id, **kwargs)
    elif media.kind == "animation":
        await bot.send_animation(chat_id, media.file_id, **kwargs)
    elif media.kind == "video_note":
        await bot.send_video_note(chat_id, media.file_id)
        if caption:
            await bot.send_message(chat_id, caption, parse_mode=ParseMode.HTML)
    else:
        raise ValueError(f"Unsupported media kind: {media.kind}")


async def deliver_notify(
    bot: Bot,
    chat_id: int,
    *,
    text: str,
    media: MediaAttachment | None,
) -> None:
    formatted = format_broadcast(text)

    caption: str | None = None
    separate_text = formatted
    if media and media.kind != "video_note":
        if len(formatted) <= CAPTION_LIMIT:
            caption = formatted
            separate_text = ""

    if media:
        await _send_media(bot, chat_id, media, caption)
        if separate_text:
            await bot.send_message(chat_id, separate_text, parse_mode=ParseMode.HTML)
    else:
        await bot.send_message(chat_id, formatted, parse_mode=ParseMode.HTML)


async def send_user_notify(
    bot: Bot,
    chat_id: int,
    *,
    text: str,
    media: MediaAttachment | None,
) -> None:
    try:
        await deliver_notify(bot, chat_id, text=text, media=media)
    except TelegramForbiddenError:
        raise
    except Exception:
        logger.exception("notify_user: не удалось отправить %s", chat_id)
        raise


async def broadcast_notify(
    bot: Bot,
    recipients: list[User],
    *,
    text: str,
    media: MediaAttachment | None,
) -> tuple[int, int, list[int]]:
    """Возвращает (успешно, ошибки, id с ошибкой)."""
    ok = 0
    fail = 0
    failed_ids: list[int] = []

    for user in recipients:
        try:
            await deliver_notify(bot, user.telegram_id, text=text, media=media)
            ok += 1
        except TelegramForbiddenError:
            fail += 1
            failed_ids.append(user.telegram_id)
        except Exception:
            logger.exception("notify_all: не удалось отправить %s", user.telegram_id)
            fail += 1
            failed_ids.append(user.telegram_id)
        await asyncio.sleep(0.05)

    return ok, fail, failed_ids
