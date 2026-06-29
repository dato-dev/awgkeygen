from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import Message

from bot.awg.manager import AWGError, AWGManager, ClientKey
from bot.database import Database, User, UserStatus
from bot.services.keys import deliver_key, run_awg
from bot.texts import admin_action_ok, user_approved_notification, user_key_deleted

logger = logging.getLogger(__name__)


async def approve_user(
    db: Database, bot: Bot, target_id: int, approved_by: int,
) -> tuple[User | None, str | None]:
    user = await db.get_user(target_id)
    if not user:
        return None, "not_found"
    if user.status == UserStatus.APPROVED:
        return user, "already"
    user = await db.set_status(target_id, UserStatus.APPROVED, approved_by=approved_by)
    try:
        await bot.send_message(target_id, user_approved_notification())
    except Exception:
        logger.exception("Не удалось уведомить %s", target_id)
    return user, None


async def issue_key(
    db: Database,
    awg: AWGManager,
    target_id: int,
    *,
    remint: bool = False,
    resend: bool = False,
) -> tuple[ClientKey | None, str, User | None]:
    user = await db.get_user(target_id)
    if not user:
        return None, "not_found", None
    if user.status != UserStatus.APPROVED:
        return None, "not_approved", user

    if remint:
        result = await run_awg(awg.remint_key, target_id)
        await db.set_has_key(target_id, True)
        return result, "remint", user
    if resend or user.has_key:
        if not user.has_key:
            return None, "no_key", user
        result = await run_awg(awg.get_existing_key, target_id)
        return result, "resend", user
    result = await run_awg(awg.create_key, target_id)
    await db.set_has_key(target_id, True)
    return result, "created", user


async def onboard_user(
    db: Database,
    bot: Bot,
    awg: AWGManager,
    target_id: int,
    admin_id: int,
    reply: Message,
) -> None:
    user = await db.get_user(target_id)
    if not user:
        await reply.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        return

    if user.status != UserStatus.APPROVED:
        user, err = await approve_user(db, bot, target_id, admin_id)
        if err == "not_found" or user is None:
            await reply.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
            return

    user = await db.get_user(target_id)
    assert user is not None

    await reply.answer(f"⏳ Онбординг <code>{target_id}</code>...")

    try:
        if user.has_key:
            result, action, user = await issue_key(db, awg, target_id, resend=True)
        else:
            result, action, user = await issue_key(db, awg, target_id)
    except AWGError as exc:
        await reply.answer(f"❌ <b>Ошибка:</b> {exc}")
        return

    if result is None or user is None:
        await reply.answer("❌ Не удалось выдать ключ.")
        return

    action_labels = {"created": "создан", "resend": "отправлен", "remint": "перечеканен"}
    label = action_labels.get(action, action)

    await reply.answer(
        admin_action_ok(
            f"🚀 <b>Онбординг завершён</b> — ключ {label}",
            user,
            extra=f"\n📍 IP: <code>{result.ip.split('/')[0]}</code>",
        ),
    )

    try:
        await bot.send_message(target_id, "🔑 <b>Ваш VPN-ключ готов!</b>")
        await deliver_key(bot, result, remint=action == "remint", chat_id=target_id)
    except Exception:
        logger.exception("Не удалось доставить ключ %s", target_id)
        await reply.answer("⚠️ Ключ создан, но не доставлен пользователю:")
        await deliver_key(reply, result, remint=action == "remint", show_footer=False)


async def delete_user_key(
    db: Database,
    bot: Bot,
    awg: AWGManager,
    target_id: int,
    reply: Message,
) -> None:
    user = await db.get_user(target_id)
    if not user:
        await reply.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        return

    await reply.answer(f"⏳ Удаляю ключ <code>{target_id}</code>...")

    try:
        ip = await run_awg(awg.delete_key, target_id)
    except AWGError as exc:
        await reply.answer(f"❌ <b>Ошибка:</b> {exc}")
        return

    await db.set_has_key(target_id, False)
    await reply.answer(
        admin_action_ok(
            "🗑 <b>Ключ удалён</b>",
            user,
            extra=f"\n📍 IP: <code>{ip.split('/')[0]}</code>",
        ),
    )

    try:
        await bot.send_message(target_id, user_key_deleted())
    except Exception:
        logger.exception("Не удалось уведомить %s", target_id)
