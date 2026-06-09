from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.awg.manager import AWGError, AWGManager
from bot.database import Database, UserStatus
from bot.services.keys import deliver_key, run_awg
from bot.texts import (
    admin_help,
    admin_pending_list,
    admin_user_card,
    admin_users_list,
    user_approved_notification,
)

router = Router()
logger = logging.getLogger(__name__)


def _is_admin(user_id: int, admin_ids: list[int]) -> bool:
    return user_id in admin_ids


def _parse_args(command: CommandObject | None) -> tuple[int | None, list[str]]:
    if not command or not command.args:
        return None, []
    parts = command.args.split()
    try:
        return int(parts[0]), parts[1:]
    except ValueError:
        return None, parts


@router.message(Command("admin"))
async def cmd_admin(message: Message, admin_ids: list[int]) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return
    await message.answer(admin_help())


@router.message(Command("pending"))
async def cmd_pending(message: Message, db: Database, admin_ids: list[int]) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return
    users = await db.list_by_status(UserStatus.PENDING)
    await message.answer(admin_pending_list(users))


@router.message(Command("users"))
async def cmd_users(message: Message, db: Database, admin_ids: list[int]) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return
    users = await db.list_all()
    await message.answer(admin_users_list(users))


@router.message(Command("user"))
async def cmd_user_info(
    message: Message,
    command: CommandObject,
    db: Database,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return

    target_id, _ = _parse_args(command)
    if target_id is None:
        await message.answer("Использование: /user &lt;telegram_id&gt;")
        return

    user = await db.get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        return

    await message.answer(admin_user_card(user))


@router.message(Command("approve"))
async def cmd_approve(
    message: Message,
    command: CommandObject,
    bot: Bot,
    db: Database,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return

    target_id, _ = _parse_args(command)
    if target_id is None:
        await message.answer("Использование: /approve &lt;telegram_id&gt;")
        return

    user = await db.get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        return

    if user.status == UserStatus.APPROVED:
        await message.answer(f"ℹ️ <code>{target_id}</code> уже одобрен.")
        return

    user = await db.set_status(target_id, UserStatus.APPROVED, approved_by=message.from_user.id)
    assert user is not None

    await message.answer(
        f"✅ <b>Одобрено</b>\n\n"
        f"👤 {user.display_name}\n"
        f"🆔 <code>{target_id}</code>\n\n"
        f"/genkey {target_id} — выдать ключ"
    )

    try:
        await bot.send_message(target_id, user_approved_notification())
    except Exception:
        logger.exception("Не удалось уведомить пользователя %s", target_id)
        await message.answer("⚠️ Не удалось отправить уведомление пользователю.")


@router.message(Command("reject"))
async def cmd_reject(
    message: Message,
    command: CommandObject,
    bot: Bot,
    db: Database,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return

    target_id, _ = _parse_args(command)
    if target_id is None:
        await message.answer("Использование: /reject &lt;telegram_id&gt;")
        return

    user = await db.get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        return

    await db.set_status(target_id, UserStatus.REJECTED)

    await message.answer(
        f"❌ <b>Отклонено</b>\n\n"
        f"👤 {user.display_name}\n"
        f"🆔 <code>{target_id}</code>"
    )

    try:
        await bot.send_message(
            target_id,
            "❌ <b>Заявка отклонена</b>\n\n"
            "Обратитесь к администратору, если считаете это ошибкой.",
        )
    except Exception:
        logger.exception("Не удалось уведомить пользователя %s", target_id)


@router.message(Command("revoke"))
async def cmd_revoke(
    message: Message,
    command: CommandObject,
    bot: Bot,
    db: Database,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return

    target_id, _ = _parse_args(command)
    if target_id is None:
        await message.answer("Использование: /revoke &lt;telegram_id&gt;")
        return

    user = await db.get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        return

    await db.set_status(target_id, UserStatus.REVOKED)

    await message.answer(
        f"🚫 <b>Доступ отозван</b>\n\n"
        f"👤 {user.display_name}\n"
        f"🆔 <code>{target_id}</code>"
    )

    try:
        await bot.send_message(
            target_id,
            "🚫 <b>Доступ отозван</b>\n\n"
            "Вы больше не можете использовать бота.",
        )
    except Exception:
        logger.exception("Не удалось уведомить пользователя %s", target_id)


@router.message(Command("repair"))
async def cmd_repair(
    message: Message,
    command: CommandObject,
    bot: Bot,
    db: Database,
    awg: AWGManager,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return

    target_id, _ = _parse_args(command)
    if target_id is None:
        await message.answer("Использование: /repair &lt;telegram_id&gt;")
        return

    user = await db.get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        return

    await message.answer(f"⏳ Чиню peer для <code>{target_id}</code>...")

    try:
        result = await run_awg(awg.repair_peer, target_id)
    except AWGError as exc:
        await message.answer(f"❌ <b>Ошибка:</b> {exc}")
        return

    await message.answer(
        f"✅ <b>Peer починен</b> (PSK применён на сервере)\n\n"
        f"👤 {user.display_name}\n"
        f"🆔 <code>{target_id}</code>\n"
        f"📍 IP: <code>{result.ip}</code>\n\n"
        "Переподключитесь в AmneziaVPN. Конфиг не менялся — /config если нужен повторно."
    )


@router.message(Command("genkey"))
async def cmd_genkey(
    message: Message,
    command: CommandObject,
    bot: Bot,
    db: Database,
    awg: AWGManager,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return

    target_id, extra = _parse_args(command)
    if target_id is None:
        await message.answer(
            "<b>🔑 Выдача ключей</b>\n\n"
            "/genkey &lt;id&gt; — создать и отправить ключ\n"
            "/genkey &lt;id&gt; remint — перечеканить и отправить\n"
            "/genkey &lt;id&gt; resend — повторно отправить текущий"
        )
        return

    user = await db.get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        return

    if user.status != UserStatus.APPROVED:
        await message.answer(
            f"❌ Не одобрен (статус: {user.status.value}).\n"
            f"Сначала: /approve {target_id}"
        )
        return

    remint = "remint" in extra
    resend = "resend" in extra

    await message.answer(f"⏳ Обрабатываю запрос для <code>{target_id}</code>...")

    try:
        if remint:
            result = await run_awg(awg.remint_key, target_id)
            await db.set_has_key(target_id, True)
            action = "перечеканен"
        elif resend or user.has_key:
            if not user.has_key and resend:
                await message.answer(f"❌ У <code>{target_id}</code> нет ключа. Используйте /genkey {target_id}")
                return
            result = await run_awg(awg.get_existing_key, target_id)
            action = "отправлен повторно"
        else:
            result = await run_awg(awg.create_key, target_id)
            await db.set_has_key(target_id, True)
            action = "создан"
    except AWGError as exc:
        await message.answer(f"❌ <b>Ошибка:</b> {exc}")
        return

    await message.answer(
        f"✅ <b>Ключ {action}</b>\n\n"
        f"👤 {user.display_name}\n"
        f"🆔 <code>{target_id}</code>\n"
        f"📍 IP: <code>{result.ip}</code>"
    )

    user_notified = False
    try:
        await bot.send_message(
            target_id,
            f"🔑 <b>Администратор выдал вам VPN-ключ</b>",
        )
        await deliver_key(bot, result, remint=remint, chat_id=target_id)
        user_notified = True
    except Exception:
        logger.exception("Не удалось отправить ключ пользователю %s", target_id)

    if not user_notified:
        await message.answer("⚠️ Не удалось доставить пользователю. Конфиг для админа:")
        await deliver_key(message, result, remint=remint, show_footer=False)
