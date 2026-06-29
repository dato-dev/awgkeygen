from __future__ import annotations

import logging
import re
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from bot.awg.manager import AWGError, AWGManager
from bot.config import Settings
from bot.database import Database, UserStatus
from bot.keyboards import admin_new_user_keyboard, admin_panel_keyboard, admin_user_keyboard
from bot.services.admin_actions import (
    approve_user,
    delete_user_key,
    issue_key,
    onboard_user,
)
from bot.services.keys import deliver_key, run_awg
from bot.services.notify import (
    broadcast_notify,
    extract_media,
    resolve_media_source,
    send_user_notify,
)
from bot.texts import (
    admin_action_ok,
    admin_help,
    admin_keydel_result,
    admin_keygen_help,
    admin_keygen_result,
    admin_keys_list,
    admin_new_request,
    admin_notify_all_help,
    admin_notify_all_result,
    admin_notify_user_help,
    admin_notify_user_ok,
    admin_pending_list,
    admin_traffic_all,
    admin_traffic_user,
    admin_user_card,
    admin_users_list,
    admin_version_info,
)
from bot.version import runtime_info

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


def _parse_notify_user_args(command: CommandObject | None) -> tuple[int | None, str]:
    if not command or not command.args:
        return None, ""
    parts = command.args.split(maxsplit=1)
    try:
        target_id = int(parts[0])
    except ValueError:
        return None, ""
    text = parts[1].strip() if len(parts) > 1 else ""
    return target_id, text


def _slug_label(raw: str) -> str:
    """Нормализовать метку автономного ключа: безопасные символы, ≤32."""
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw.strip()).strip("-")
    return slug[:32]


def _parse_callback_id(data: str) -> int | None:
    try:
        return int(data.split(":", 1)[1])
    except (IndexError, ValueError):
        return None


def _version_message(settings: Settings, admin_ids: list[int]) -> str:
    info = runtime_info()
    return admin_version_info(
        version=info["version"],
        python_version=info["python"],
        in_docker=info["in_docker"] == "True",
        docker_container=settings.docker_container,
        server_endpoint=settings.server_endpoint,
        awg_port=settings.awg_port,
        database_path=str(settings.database_path),
        admins_count=len(admin_ids),
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, admin_ids: list[int]) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return
    await message.answer(admin_help(), reply_markup=admin_panel_keyboard())


@router.message(Command("version"))
async def cmd_version(
    message: Message,
    settings: Settings,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return
    await message.answer(_version_message(settings, admin_ids))


@router.callback_query(F.data == "admin:version")
async def cb_admin_version(
    query: CallbackQuery,
    settings: Settings,
    admin_ids: list[int],
) -> None:
    if not query.from_user or not _is_admin(query.from_user.id, admin_ids):
        await query.answer("Нет доступа", show_alert=True)
        return
    await query.answer()
    if query.message:
        await query.message.answer(_version_message(settings, admin_ids))


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
    awg: AWGManager,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return

    target_id, _ = _parse_args(command)
    if target_id is None:
        await message.answer("Использование: <code>/user &lt;telegram_id&gt;</code>")
        return

    user = await db.get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        return

    stats = None
    if user.has_key:
        try:
            stats = await run_awg(awg.get_peer_stats, target_id)
        except AWGError:
            pass

    await message.answer(
        admin_user_card(user, stats),
        reply_markup=admin_user_keyboard(target_id, has_key=user.has_key),
    )


@router.message(Command("traffic"))
async def cmd_traffic(
    message: Message,
    command: CommandObject,
    db: Database,
    awg: AWGManager,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return

    target_id, _ = _parse_args(command)

    try:
        if target_id is not None:
            user = await db.get_user(target_id)
            if not user:
                await message.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
                return
            stats = await run_awg(awg.get_peer_stats, target_id)
            await message.answer(admin_traffic_user(user, stats))
            return

        users = await db.list_all()
        stats_map = await run_awg(awg.get_all_peer_stats)
        name_map = await run_awg(awg.get_peer_name_map)
        await message.answer(admin_traffic_all(users, stats_map, name_map))
    except AWGError as exc:
        await message.answer(f"❌ <b>Ошибка:</b> {exc}")


@router.message(Command("notify_user"))
async def cmd_notify_user(
    message: Message,
    command: CommandObject,
    bot: Bot,
    db: Database,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return

    target_id, text = _parse_notify_user_args(command)
    if target_id is None:
        await message.answer(admin_notify_user_help())
        return
    if not text:
        await message.answer(
            "Укажите текст после id:\n"
            "<code>/notify_user &lt;telegram_id&gt; Текст сообщения</code>"
        )
        return

    user = await db.get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        return

    media_source = resolve_media_source(message)
    media = extract_media(media_source) if media_source else None

    try:
        await send_user_notify(bot, target_id, text=text, media=media)
    except TelegramForbiddenError:
        await message.answer(
            f"❌ Не удалось доставить — пользователь <code>{target_id}</code> "
            "заблокировал бота или не начинал диалог."
        )
        return
    except Exception:
        await message.answer(f"❌ <b>Ошибка</b> при отправке пользователю <code>{target_id}</code>.")
        return

    await message.answer(admin_notify_user_ok(user, with_attachment=media is not None))


@router.message(Command("notify_all"))
async def cmd_notify_all(
    message: Message,
    command: CommandObject,
    bot: Bot,
    db: Database,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return

    text = (command.args or "").strip()
    if not text:
        await message.answer(admin_notify_all_help())
        return

    users = await db.list_by_status(UserStatus.APPROVED)
    recipients = [u for u in users if u.telegram_id not in admin_ids]
    if not recipients:
        await message.answer("ℹ️ Нет одобренных пользователей для рассылки.")
        return

    media_source = resolve_media_source(message)
    media = extract_media(media_source) if media_source else None

    await message.answer(
        f"📤 <b>Рассылка...</b>\n\n"
        f"👥 Получателей: <b>{len(recipients)}</b>"
        + ("\n📎 С вложением" if media else ""),
    )

    ok, fail, _ = await broadcast_notify(
        bot,
        recipients,
        text=text,
        media=media,
    )

    await message.answer(
        admin_notify_all_result(
            ok,
            fail,
            len(recipients),
            with_attachment=media is not None,
        ),
    )


@router.message(Command("onboard"))
async def cmd_onboard(
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
        await message.answer(
            "🚀 <b>Онбординг</b>\n\n"
            "Одобряет пользователя и сразу выдаёт ключ.\n\n"
            "<code>/onboard &lt;telegram_id&gt;</code>"
        )
        return

    await onboard_user(db, bot, awg, target_id, message.from_user.id, message)


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
        await message.answer("Использование: <code>/approve &lt;telegram_id&gt;</code>")
        return

    user, err = await approve_user(db, bot, target_id, message.from_user.id)
    if err == "not_found" or user is None:
        await message.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        return
    if err == "already":
        await message.answer(
            admin_action_ok("ℹ️ <b>Уже одобрен</b>", user),
            reply_markup=admin_user_keyboard(target_id, has_key=user.has_key),
        )
        return

    await message.answer(
        admin_action_ok(
            "✅ <b>Одобрено</b>",
            user,
            extra=f"\n\n🚀 <code>/onboard {target_id}</code>",
        ),
        reply_markup=admin_user_keyboard(target_id, has_key=user.has_key),
    )


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
        await message.answer("Использование: <code>/reject &lt;telegram_id&gt;</code>")
        return

    user = await db.get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        return

    await db.set_status(target_id, UserStatus.REJECTED)
    await message.answer(admin_action_ok("❌ <b>Отклонено</b>", user))

    try:
        await bot.send_message(
            target_id,
            "❌ <b>Заявка отклонена</b>\n\nОбратитесь к администратору.",
        )
    except Exception:
        logger.exception("Не удалось уведомить %s", target_id)


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
        await message.answer("Использование: <code>/revoke &lt;telegram_id&gt;</code>")
        return

    user = await db.get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        return

    await db.set_status(target_id, UserStatus.REVOKED)
    await message.answer(admin_action_ok("🚫 <b>Доступ отозван</b>", user))

    try:
        await bot.send_message(target_id, "🚫 <b>Доступ отозван</b>")
    except Exception:
        logger.exception("Не удалось уведомить %s", target_id)


@router.message(Command("delkey"))
async def cmd_delkey(
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
        await message.answer(
            "🗑 <b>Удаление ключа</b>\n\n"
            "Удаляет peer с сервера AWG.\n\n"
            "<code>/delkey &lt;telegram_id&gt;</code>"
        )
        return

    await delete_user_key(db, bot, awg, target_id, message)


@router.message(Command("repair"))
async def cmd_repair(
    message: Message,
    command: CommandObject,
    db: Database,
    awg: AWGManager,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return

    target_id, _ = _parse_args(command)
    if target_id is None:
        await message.answer("Использование: <code>/repair &lt;telegram_id&gt;</code>")
        return

    user = await db.get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        return

    await message.answer(f"⏳ Чиню peer <code>{target_id}</code>...")

    try:
        result = await run_awg(awg.repair_peer, target_id)
    except AWGError as exc:
        await message.answer(f"❌ <b>Ошибка:</b> {exc}")
        return

    await message.answer(
        admin_action_ok(
            "🔧 <b>Peer починен</b> (PSK применён)",
            user,
            extra=f"\n📍 IP: <code>{result.ip.split('/')[0]}</code>",
        ),
        reply_markup=admin_user_keyboard(target_id, has_key=True),
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
            "🔑 <b>Выдача ключей</b>\n\n"
            "<code>/genkey &lt;id&gt;</code> — создать\n"
            "<code>/genkey &lt;id&gt; remint</code> — перечеканить\n"
            "<code>/genkey &lt;id&gt; resend</code> — повторно отправить"
        )
        return

    remint = "remint" in extra
    resend = "resend" in extra

    await message.answer(f"⏳ Обрабатываю <code>{target_id}</code>...")

    try:
        result, action, user = await issue_key(
            db, awg, target_id, remint=remint, resend=resend,
        )
    except AWGError as exc:
        await message.answer(f"❌ <b>Ошибка:</b> {exc}")
        return

    if result is None or user is None:
        if action == "not_found":
            await message.answer(f"❌ Пользователь <code>{target_id}</code> не найден.")
        elif action == "not_approved":
            await message.answer(f"❌ Сначала <code>/approve {target_id}</code>")
        elif action == "no_key":
            await message.answer(f"❌ Нет ключа. <code>/genkey {target_id}</code>")
        return

    labels = {"created": "создан", "remint": "перечеканен", "resend": "отправлен"}
    await message.answer(
        admin_action_ok(
            f"✅ <b>Ключ {labels.get(action, action)}</b>",
            user,
            extra=f"\n📍 IP: <code>{result.ip.split('/')[0]}</code>",
        ),
        reply_markup=admin_user_keyboard(target_id, has_key=True),
    )

    try:
        await bot.send_message(target_id, "🔑 <b>Администратор выдал вам VPN-ключ</b>")
        await deliver_key(bot, result, remint=remint, chat_id=target_id)
    except Exception:
        logger.exception("Не удалось доставить ключ %s", target_id)
        await message.answer("⚠️ Не доставлено пользователю. Конфиг ниже:")
        await deliver_key(message, result, remint=remint, show_footer=False)


@router.message(Command("keygen"))
async def cmd_keygen(
    message: Message,
    command: CommandObject,
    awg: AWGManager,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return

    raw = (command.args or "").strip()
    label = _slug_label(raw)
    if raw and not label:
        await message.answer(
            "❌ Метка содержит только недопустимые символы.\n"
            "Используйте латиницу, цифры, <code>-</code> и <code>_</code>."
        )
        return
    if not label:
        label = datetime.now().strftime("%m%d-%H%M%S")

    await message.answer(f"⏳ Создаю ключ <code>{label}</code>...")

    try:
        result = await run_awg(awg.create_manual_key, label)
    except AWGError as exc:
        await message.answer(f"❌ <b>Ошибка:</b> {exc}")
        return

    await message.answer(admin_keygen_result(label, result.ip.split("/")[0]))
    await deliver_key(
        message, result, remint=False, show_header=False, show_footer=False,
    )


@router.message(Command("keys"))
async def cmd_keys(
    message: Message,
    awg: AWGManager,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return

    try:
        keys = await run_awg(awg.list_manual_keys)
    except AWGError as exc:
        await message.answer(f"❌ <b>Ошибка:</b> {exc}")
        return

    await message.answer(admin_keys_list(keys))


@router.message(Command("keydel"))
async def cmd_keydel(
    message: Message,
    command: CommandObject,
    awg: AWGManager,
    admin_ids: list[int],
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        return

    label = _slug_label(command.args or "")
    if not label:
        await message.answer(admin_keygen_help())
        return

    await message.answer(f"⏳ Удаляю ключ <code>{label}</code>...")

    try:
        ip = await run_awg(awg.delete_manual_key, label)
    except AWGError as exc:
        await message.answer(f"❌ <b>Ошибка:</b> {exc}")
        return

    await message.answer(admin_keydel_result(label, ip.split("/")[0]))


# ── Callback-кнопки ──────────────────────────────────────────

@router.callback_query(F.data.startswith("onboard:"))
async def cb_onboard(
    query: CallbackQuery, bot: Bot, db: Database, awg: AWGManager, admin_ids: list[int],
) -> None:
    if not query.from_user or not _is_admin(query.from_user.id, admin_ids):
        await query.answer("Нет доступа", show_alert=True)
        return
    target_id = _parse_callback_id(query.data or "")
    if target_id is None:
        await query.answer("Ошибка ID", show_alert=True)
        return
    await query.answer("🚀 Онбординг...")
    await onboard_user(db, bot, awg, target_id, query.from_user.id, query.message)
    if query.message:
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass


@router.callback_query(F.data.startswith("approve:"))
async def cb_approve(
    query: CallbackQuery, bot: Bot, db: Database, admin_ids: list[int],
) -> None:
    if not query.from_user or not _is_admin(query.from_user.id, admin_ids):
        await query.answer("Нет доступа", show_alert=True)
        return
    target_id = _parse_callback_id(query.data or "")
    if target_id is None:
        return
    user, err = await approve_user(db, bot, target_id, query.from_user.id)
    if user is None:
        await query.answer("Не найден", show_alert=True)
        return
    await query.answer("✅ Одобрено")
    if query.message:
        await query.message.answer(
            admin_action_ok("✅ <b>Одобрено</b>", user),
            reply_markup=admin_user_keyboard(target_id, has_key=user.has_key),
        )


@router.callback_query(F.data.startswith("reject:"))
async def cb_reject(
    query: CallbackQuery, bot: Bot, db: Database, admin_ids: list[int],
) -> None:
    if not query.from_user or not _is_admin(query.from_user.id, admin_ids):
        await query.answer("Нет доступа", show_alert=True)
        return
    target_id = _parse_callback_id(query.data or "")
    if target_id is None:
        return
    user = await db.get_user(target_id)
    if not user:
        await query.answer("Не найден", show_alert=True)
        return
    await db.set_status(target_id, UserStatus.REJECTED)
    await query.answer("❌ Отклонено")
    try:
        await bot.send_message(target_id, "❌ <b>Заявка отклонена</b>")
    except Exception:
        pass


@router.callback_query(F.data.startswith("revoke:"))
async def cb_revoke(
    query: CallbackQuery, bot: Bot, db: Database, admin_ids: list[int],
) -> None:
    if not query.from_user or not _is_admin(query.from_user.id, admin_ids):
        await query.answer("Нет доступа", show_alert=True)
        return
    target_id = _parse_callback_id(query.data or "")
    if target_id is None:
        return
    user = await db.get_user(target_id)
    if not user:
        await query.answer("Не найден", show_alert=True)
        return
    await db.set_status(target_id, UserStatus.REVOKED)
    await query.answer("🚫 Отозвано")
    try:
        await bot.send_message(target_id, "🚫 <b>Доступ отозван</b>")
    except Exception:
        pass


@router.callback_query(F.data.startswith("genkey:"))
async def cb_genkey(
    query: CallbackQuery, bot: Bot, db: Database, awg: AWGManager, admin_ids: list[int],
) -> None:
    if not query.from_user or not _is_admin(query.from_user.id, admin_ids):
        await query.answer("Нет доступа", show_alert=True)
        return
    target_id = _parse_callback_id(query.data or "")
    if target_id is None or not query.message:
        return
    await query.answer("🔑 Генерирую...")
    try:
        result, action, user = await issue_key(db, awg, target_id)
    except AWGError as exc:
        await query.answer(str(exc)[:200], show_alert=True)
        return
    if result is None or user is None:
        await query.answer("Ошибка", show_alert=True)
        return
    await deliver_key(bot, result, remint=False, chat_id=target_id)
    await query.message.answer(admin_action_ok("✅ <b>Ключ выдан</b>", user))


@router.callback_query(F.data.startswith("delkey:"))
async def cb_delkey(
    query: CallbackQuery, bot: Bot, db: Database, awg: AWGManager, admin_ids: list[int],
) -> None:
    if not query.from_user or not _is_admin(query.from_user.id, admin_ids):
        await query.answer("Нет доступа", show_alert=True)
        return
    target_id = _parse_callback_id(query.data or "")
    if target_id is None or not query.message:
        return
    await query.answer("🗑 Удаляю...")
    await delete_user_key(db, bot, awg, target_id, query.message)


@router.callback_query(F.data.startswith("repair:"))
async def cb_repair(
    query: CallbackQuery, db: Database, awg: AWGManager, admin_ids: list[int],
) -> None:
    if not query.from_user or not _is_admin(query.from_user.id, admin_ids):
        await query.answer("Нет доступа", show_alert=True)
        return
    target_id = _parse_callback_id(query.data or "")
    if target_id is None or not query.message:
        return
    await query.answer("🔧 Чиню...")
    try:
        await run_awg(awg.repair_peer, target_id)
        await query.message.answer(f"✅ Peer <code>{target_id}</code> починен")
    except AWGError as exc:
        await query.answer(str(exc)[:200], show_alert=True)
