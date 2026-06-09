import logging

from aiogram import Bot, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.awg.manager import AWGError, AWGManager
from bot.database import Database, UserStatus
from bot.services.keys import deliver_key, run_awg
from bot.texts import (
    user_help,
    user_status,
    user_welcome_approved,
    user_welcome_denied,
    user_welcome_pending,
)

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    bot: Bot,
    db: Database,
    admin_ids: list[int],
) -> None:
    user, is_new = await db.upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    if message.from_user.id in admin_ids:
        from bot.texts import admin_help
        await message.answer(admin_help())
        return

    if user.status == UserStatus.PENDING:
        if is_new:
            from bot.texts import admin_new_request
            text = admin_new_request(user)
            for admin_id in admin_ids:
                try:
                    await bot.send_message(admin_id, text)
                except Exception:
                    logger.exception("Не удалось уведомить админа %s", admin_id)
        await message.answer(user_welcome_pending())
        return

    if user.status == UserStatus.APPROVED:
        await message.answer(user_welcome_approved(user.has_key))
        return

    await message.answer(user_welcome_denied(user.status))


@router.message(Command("help"))
async def cmd_help(message: Message, db: Database, admin_ids: list[int]) -> None:
    if message.from_user.id in admin_ids:
        from bot.texts import admin_help
        await message.answer(admin_help())
        return

    user = await db.get_user(message.from_user.id)
    has_key = user.has_key if user else False
    await message.answer(user_help(has_key))


@router.message(Command("status"))
async def cmd_status(message: Message, db: Database, admin_ids: list[int]) -> None:
    if message.from_user.id in admin_ids:
        return

    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Вы не зарегистрированы. Нажмите /start")
        return

    await message.answer(user_status(user))


@router.message(Command("key"))
async def cmd_key(
    message: Message,
    db: Database,
    awg: AWGManager,
    admin_ids: list[int],
) -> None:
    if message.from_user.id in admin_ids:
        return

    user = await db.get_user(message.from_user.id)
    if not user or user.status != UserStatus.APPROVED:
        await message.answer(
            "❌ <b>Нет доступа</b>\n\n"
            "Дождитесь одобрения администратора.\n"
            "Статус: /status"
        )
        return

    if user.has_key:
        await message.answer(
            "ℹ️ Ключ уже выдан.\n\n"
            "/config — показать конфиг\n"
            "/remint — перечеканить ключ"
        )
        return

    await message.answer("⏳ Генерирую ключ...")

    try:
        result = await run_awg(awg.create_key, message.from_user.id)
    except AWGError as exc:
        await message.answer(f"❌ <b>Ошибка:</b> {exc}")
        return

    await db.set_has_key(message.from_user.id, True)
    await deliver_key(message, result, remint=False)


@router.message(Command("remint"))
async def cmd_remint(
    message: Message,
    db: Database,
    awg: AWGManager,
    admin_ids: list[int],
) -> None:
    if message.from_user.id in admin_ids:
        return

    user = await db.get_user(message.from_user.id)
    if not user or user.status != UserStatus.APPROVED:
        await message.answer("❌ <b>Нет доступа</b>")
        return

    if not user.has_key:
        await message.answer("У вас ещё нет ключа. Используйте /key")
        return

    await message.answer("⏳ Перечеканиваю ключ...")

    try:
        result = await run_awg(awg.remint_key, message.from_user.id)
    except AWGError as exc:
        await message.answer(f"❌ <b>Ошибка:</b> {exc}")
        return

    await deliver_key(message, result, remint=True)


@router.message(Command("config"))
async def cmd_config(
    message: Message,
    db: Database,
    awg: AWGManager,
    admin_ids: list[int],
) -> None:
    if message.from_user.id in admin_ids:
        return

    user = await db.get_user(message.from_user.id)
    if not user or user.status != UserStatus.APPROVED or not user.has_key:
        await message.answer("❌ Ключ не найден. Получите его: /key")
        return

    await message.answer("⏳ Получаю конфиг...")

    try:
        result = await run_awg(awg.get_existing_key, message.from_user.id)
    except AWGError as exc:
        await message.answer(f"❌ <b>Ошибка:</b> {exc}")
        return

    await deliver_key(message, result, remint=False, show_footer=False)
